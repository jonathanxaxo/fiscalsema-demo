"""Login com Google, vínculo seguro e Minha conta (Sprint 25).

O Google é simulado: ``exchange_code`` é substituído; nada acessa a internet.
"""

import base64
import json
import time
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.test import TestCase, override_settings
from django.urls import reverse

from accounts import google_oidc
from accounts.models import AccountStatus, AuthenticationEvent, ExternalIdentity, User, UserProfile
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

GOOGLE = {"GOOGLE_OAUTH_CLIENT_ID": "cliente-ficticio.apps.googleusercontent.com",
          "GOOGLE_OAUTH_CLIENT_SECRET": "segredo-ficticio"}


def _b64(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def id_token(**overrides):
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "aud": GOOGLE["GOOGLE_OAUTH_CLIENT_ID"],
        "sub": "google-sub-123",
        "email": "fiscal.google@example.local",
        "email_verified": True,
        "name": "Nome no Google",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return f"{_b64({'alg': 'RS256'})}.{_b64(claims)}.assinatura"


@override_settings(**GOOGLE)
class GoogleBase(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Organização Google")
        self.user = User.objects.create_user(
            email="fiscal.google@example.local", full_name="Fiscal Cadastro Original",
            password=VALID_PASSWORD, status=AccountStatus.ACTIVE, organization=self.organization,
        )

    def start(self, url_name="accounts:google_start", **post):
        response = self.client.post(reverse(url_name), post) if post else self.client.get(reverse(url_name))
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlparse(response["Location"]).query)
        return query, self.client.session[google_oidc.SESSION_KEY]

    def callback(self, *, token_claims=None, state=None, exchange_error=None):
        query, flow = self.start()
        token_claims = {"nonce": flow["nonce"], **(token_claims or {})}
        side = exchange_error or None
        with mock.patch.object(google_oidc, "exchange_code",
                               side_effect=side, return_value={"id_token": id_token(**token_claims)}) as patched:
            response = self.client.get(reverse("accounts:google_callback"),
                                       {"state": state or query["state"][0], "code": "codigo-ficticio"})
        return response, patched

    def snapshot(self, user):
        user.refresh_from_db()
        return (user.pk, user.full_name, user.profile, user.organization_id, user.status, user.password)


class GoogleFlowTests(GoogleBase):
    def test_start_uses_pkce_state_and_nonce(self):
        query, flow = self.start()
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["scope"], ["openid email profile"])
        self.assertEqual(query["state"], [flow["state"]])
        self.assertEqual(query["nonce"], [flow["nonce"]])
        self.assertTrue(query["redirect_uri"][0].endswith(reverse("accounts:google_callback")))

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="", GOOGLE_OAUTH_CLIENT_SECRET="")
    def test_button_always_visible_and_friendly_when_not_configured(self):
        login = self.client.get(reverse("accounts:login"))
        self.assertContains(login, "Entrar com Google")
        self.assertContains(login, "Opcional")
        response = self.client.get(reverse("accounts:google_start"))
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertContains(self.client.get(response["Location"]), "ainda está sendo configurado")
        self.assertEqual(self.client.get(reverse("accounts:google_callback")).status_code, 404)

    def test_password_login_still_first_option(self):
        login = self.client.get(reverse("accounts:login")).content.decode()
        self.assertLess(login.index('type="submit">Entrar</button>'), login.index("Entrar com Google"))

    def test_already_linked_logs_into_same_user_without_changes(self):
        ExternalIdentity.objects.create(user=self.user, provider="google", subject="google-sub-123",
                                        email=self.user.email)
        before = self.snapshot(self.user)
        response, _ = self.callback(token_claims={"name": "Outro Nome", "email": "outro@example.local"})
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.assertEqual(self.snapshot(self.user), before)
        self.assertTrue(AuthenticationEvent.objects.filter(user=self.user, event_type="LOGIN_GOOGLE").exists())

    def test_blocked_and_pending_users_cannot_enter(self):
        ExternalIdentity.objects.create(user=self.user, provider="google", subject="google-sub-123",
                                        email=self.user.email)
        for status, text in ((AccountStatus.BLOCKED, "não está ativa"),
                             (AccountStatus.PENDING_APPROVAL, "aguarda aprovação")):
            with self.subTest(status=status):
                User.objects.filter(pk=self.user.pk).update(status=status)
                response, _ = self.callback()
                self.assertNotIn("_auth_user_id", self.client.session)
                self.assertContains(self.client.get(response["Location"]), text)

    def test_same_email_requires_password_before_linking(self):
        before = self.snapshot(self.user)
        response, _ = self.callback()
        self.assertRedirects(response, reverse("accounts:google_confirm_link"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(ExternalIdentity.objects.exists())
        wrong = self.client.post(reverse("accounts:google_confirm_link"), {"password": "senha-errada"})
        self.assertEqual(wrong.status_code, 400)
        self.assertFalse(ExternalIdentity.objects.exists())
        ok = self.client.post(reverse("accounts:google_confirm_link"), {"password": VALID_PASSWORD})
        self.assertRedirects(ok, reverse("home"), fetch_redirect_response=False)
        identity = ExternalIdentity.objects.get()
        self.assertEqual((identity.user, identity.subject), (self.user, "google-sub-123"))
        self.assertEqual(self.snapshot(self.user), before)
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(AuthenticationEvent.objects.filter(event_type="GOOGLE_VINCULADO").exists())

    def test_pending_link_expires(self):
        self.callback()
        session = self.client.session
        session["fiscalsema_google_pending_link"]["expires"] = 0
        session.save()
        response = self.client.post(reverse("accounts:google_confirm_link"), {"password": VALID_PASSWORD})
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(ExternalIdentity.objects.exists())

    def test_unknown_email_is_refused_and_no_user_created(self):
        response, _ = self.callback(token_claims={"email": "desconhecido@example.local", "sub": "outro-sub"})
        self.assertContains(self.client.get(response["Location"]), "Não encontramos cadastro")
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(AuthenticationEvent.objects.filter(event_type="LOGIN_GOOGLE_NEGADO").exists())

    def test_invalid_tokens_are_refused(self):
        cases = {
            "e-mail não verificado": {"email_verified": False},
            "outro aplicativo": {"aud": "outro-cliente"},
            "emissor": {"iss": "https://falso.example"},
            "expirado": {"exp": int(time.time()) - 3600},
            "nonce": {"nonce": "nonce-falso"},
        }
        for label, claims in cases.items():
            with self.subTest(label):
                response, _ = self.callback(token_claims=claims)
                self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
                self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(ExternalIdentity.objects.exists())

    def test_wrong_state_is_refused_without_calling_google(self):
        response, patched = self.callback(state="state-adulterado")
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        patched.assert_not_called()

    def test_provider_failure_shows_friendly_message(self):
        error = google_oidc.GoogleLoginError("Não foi possível falar com o Google agora. Tente novamente.")
        response, _ = self.callback(exchange_error=error)
        self.assertContains(self.client.get(response["Location"]), "Não foi possível falar com o Google")

    def test_user_cancelled_at_google(self):
        self.start()
        response = self.client.get(reverse("accounts:google_callback"), {"error": "access_denied"})
        self.assertContains(self.client.get(response["Location"]), "cancelado")


class MinhaContaTests(GoogleBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_page_and_topbar_link(self):
        page = self.client.get(reverse("accounts:my_account"))
        self.assertContains(page, "Métodos de acesso")
        self.assertContains(page, "Conexões externas")
        self.assertContains(page, "Vincular conta Google")
        self.assertContains(self.client.get(reverse("home")), 'href="/conta/minha-conta/"')

    def test_link_requires_current_password(self):
        response = self.client.post(reverse("accounts:google_link_start"), {"password": "errada"})
        self.assertRedirects(response, reverse("accounts:my_account"), fetch_redirect_response=False)
        self.assertNotIn(google_oidc.SESSION_KEY, self.client.session)

    def link(self, sub="google-sub-123"):
        query, flow = self.start("accounts:google_link_start", password=VALID_PASSWORD)
        with mock.patch.object(google_oidc, "exchange_code",
                               return_value={"id_token": id_token(nonce=flow["nonce"], sub=sub)}):
            return self.client.get(reverse("accounts:google_callback"),
                                   {"state": query["state"][0], "code": "codigo"})

    def test_link_from_my_account(self):
        before = self.snapshot(self.user)
        self.link()
        self.assertEqual(ExternalIdentity.objects.get().user, self.user)
        self.assertEqual(self.snapshot(self.user), before)

    def test_google_of_another_user_cannot_be_linked(self):
        other = User.objects.create_user(email="outro.google@example.local", full_name="Outro",
                                         password=VALID_PASSWORD, status=AccountStatus.ACTIVE)
        ExternalIdentity.objects.create(user=other, provider="google", subject="google-sub-123", email=other.email)
        response = self.link()
        self.assertContains(self.client.get(response["Location"]), "vinculada a outro usuário")
        self.assertEqual(ExternalIdentity.objects.get().user, other)

    def test_unlink_requires_password_and_keeps_one_method(self):
        identity = ExternalIdentity.objects.create(user=self.user, provider="google", subject="s1", email=self.user.email)
        self.client.post(reverse("accounts:google_unlink", args=[identity.pk]), {"password": "errada"})
        self.assertTrue(ExternalIdentity.objects.filter(pk=identity.pk).exists())
        self.client.post(reverse("accounts:google_unlink", args=[identity.pk]), {"password": VALID_PASSWORD})
        self.assertFalse(ExternalIdentity.objects.filter(pk=identity.pk).exists())
        self.assertTrue(AuthenticationEvent.objects.filter(event_type="GOOGLE_DESVINCULADO").exists())

    def test_cannot_remove_only_access_method(self):
        identity = ExternalIdentity.objects.create(user=self.user, provider="google", subject="s1", email=self.user.email)
        self.user.set_unusable_password()
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.post(reverse("accounts:google_unlink", args=[identity.pk]), {"password": "x"})
        self.assertContains(self.client.get(response["Location"]), "única forma de acesso")
        self.assertTrue(ExternalIdentity.objects.filter(pk=identity.pk).exists())

    def test_cannot_unlink_identity_of_other_user(self):
        other = User.objects.create_user(email="dono@example.local", full_name="Dono", password=VALID_PASSWORD,
                                         status=AccountStatus.ACTIVE)
        identity = ExternalIdentity.objects.create(user=other, provider="google", subject="s9", email=other.email)
        response = self.client.post(reverse("accounts:google_unlink", args=[identity.pk]), {"password": VALID_PASSWORD})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ExternalIdentity.objects.filter(pk=identity.pk).exists())

    def test_profile_is_never_changed_by_google(self):
        User.objects.filter(pk=self.user.pk).update(profile=UserProfile.CONSULTATION)
        self.link()
        self.user.refresh_from_db()
        self.assertEqual(self.user.profile, UserProfile.CONSULTATION)
