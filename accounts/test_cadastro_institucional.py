"""Cadastro institucional pelo Google e política de e-mails (Sprint 27).

Domínios e e-mails fictícios; Google simulado (sem internet).
"""

from unittest import mock

from django.test import override_settings
from django.urls import reverse

from accounts import google_oidc
from accounts.forms import FiscalRegistrationForm
from accounts.models import (
    AccountStatus, AuthenticationEvent, ExternalIdentity, RegistrationRequest, RegistrationStatus, User, UserProfile,
)
from accounts.services import review_registration_request
from accounts.signup_policy import is_signup_allowed
from accounts.test_google_login import GOOGLE, GoogleBase, id_token
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization

POLICY = {
    **GOOGLE,
    "ALLOWED_SIGNUP_DOMAINS": ["instituicao.example"],
    "ALLOWED_SIGNUP_EMAILS": ["professor@escola.example"],
    "GOOGLE_REQUIRE_HOSTED_DOMAIN": False,
}


@override_settings(**POLICY)
class PoliticaTests(GoogleBase):
    def test_policy_rules(self):
        self.assertTrue(is_signup_allowed("Servidor@Instituicao.example"))
        self.assertTrue(is_signup_allowed("professor@escola.example"))
        self.assertFalse(is_signup_allowed("colega@escola.example"))
        self.assertFalse(is_signup_allowed("pessoa@gmail.com"))
        self.assertFalse(is_signup_allowed("instituicao.example"))

    @override_settings(ALLOWED_SIGNUP_DOMAINS=[], ALLOWED_SIGNUP_EMAILS=[])
    def test_empty_policy_allows_nobody(self):
        self.assertFalse(is_signup_allowed("servidor@instituicao.example"))

    @override_settings(GOOGLE_REQUIRE_HOSTED_DOMAIN=True)
    def test_hosted_domain_required_when_enabled(self):
        self.assertFalse(is_signup_allowed("servidor@instituicao.example", hosted_domain=""))
        self.assertTrue(is_signup_allowed("servidor@instituicao.example", hosted_domain="instituicao.example"))
        # a exceção individual não depende de Workspace
        self.assertTrue(is_signup_allowed("professor@escola.example", hosted_domain=""))

    def test_password_registration_form_applies_policy(self):
        data = {"full_name": "Pessoa", "organization_name": "Org", "password1": "SenhaForte!2026x",
                "password2": "SenhaForte!2026x"}
        refused = FiscalRegistrationForm(data={**data, "email": "pessoa@gmail.com"})
        self.assertFalse(refused.is_valid())
        self.assertIn("não está autorizado", str(refused.errors["email"]))


@override_settings(**POLICY)
class CadastroGoogleTests(GoogleBase):
    def google_as(self, email, sub, **claims):
        response, _ = self.callback(token_claims={"email": email, "sub": sub, "name": "Nome Google", **claims})
        return response

    def complete(self, **data):
        payload = {"full_name": "Servidora Fictícia", "organization_name": "Secretaria Fictícia", **data}
        return self.client.post(reverse("accounts:google_signup"), payload)

    def test_new_institutional_user_becomes_pending_with_google_link(self):
        response = self.google_as("nova@instituicao.example", "sub-nova")
        self.assertRedirects(response, reverse("accounts:google_signup"), fetch_redirect_response=False)
        form = self.client.get(reverse("accounts:google_signup"))
        self.assertContains(form, "nova@instituicao.example")
        self.assertContains(form, 'value="Nome Google"')
        done = self.complete()
        self.assertContains(done, "aguardando aprovação")
        user = User.objects.get(email="nova@instituicao.example")
        self.assertEqual(user.status, AccountStatus.PENDING_APPROVAL)
        self.assertEqual(user.profile, UserProfile.FISCAL)
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertIsNone(user.organization_id)
        self.assertEqual(RegistrationRequest.objects.get(user=user).status, RegistrationStatus.PENDING)
        self.assertEqual(ExternalIdentity.objects.get(user=user).subject, "sub-nova")
        self.assertNotIn("_auth_user_id", self.client.session)
        event = AuthenticationEvent.objects.get(user=user, event_type="CADASTRO_SOLICITADO")
        self.assertEqual(event.details["origem"], "google")

    def test_professor_exception_is_exact(self):
        self.google_as("professor@escola.example", "sub-prof")
        self.complete(full_name="Professor Fictício", organization_name="Escola Fictícia")
        professor = User.objects.get(email="professor@escola.example")
        self.assertEqual(professor.status, AccountStatus.PENDING_APPROVAL)
        self.assertFalse(professor.is_staff)
        self.assertNotEqual(professor.profile, UserProfile.ADMINISTRATOR)
        response = self.google_as("colega@escola.example", "sub-colega")
        self.assertContains(self.client.get(response["Location"]), "não está autorizado")
        self.assertFalse(User.objects.filter(email="colega@escola.example").exists())

    def test_personal_email_is_refused(self):
        response = self.google_as("pessoa@gmail.com", "sub-gmail")
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(email="pessoa@gmail.com").exists())

    def test_unverified_email_never_reaches_signup(self):
        response = self.google_as("nova@instituicao.example", "sub-x", email_verified=False)
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertNotIn("fiscalsema_google_pending_signup", self.client.session)

    @override_settings(GOOGLE_REQUIRE_HOSTED_DOMAIN=True)
    def test_domain_without_workspace_proof_is_refused_when_required(self):
        response = self.google_as("nova@instituicao.example", "sub-sem-hd")
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        response = self.google_as("nova@instituicao.example", "sub-com-hd", hd="instituicao.example")
        self.assertRedirects(response, reverse("accounts:google_signup"), fetch_redirect_response=False)

    def test_duplicate_is_prevented(self):
        self.google_as("dup@instituicao.example", "sub-dup")
        User.objects.create_user(email="dup@instituicao.example", full_name="Criado Antes",
                                 password=VALID_PASSWORD, status=AccountStatus.ACTIVE)
        response = self.complete()
        self.assertRedirects(response, reverse("accounts:login"), fetch_redirect_response=False)
        self.assertEqual(User.objects.filter(email="dup@instituicao.example").count(), 1)
        self.assertFalse(ExternalIdentity.objects.filter(subject="sub-dup").exists())

    def test_signup_session_expires(self):
        self.google_as("tarde@instituicao.example", "sub-tarde")
        session = self.client.session
        session["fiscalsema_google_pending_signup"]["expires"] = 0
        session.save()
        self.assertRedirects(self.complete(), reverse("accounts:login"), fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(email="tarde@instituicao.example").exists())

    def test_pending_cannot_enter_then_enters_after_approval(self):
        self.google_as("aprovar@instituicao.example", "sub-aprovar")
        self.complete()
        response = self.google_as("aprovar@instituicao.example", "sub-aprovar")
        self.assertContains(self.client.get(response["Location"]), "aguarda aprovação")
        admin = User.objects.create_superuser(email="admin.cad@example.local", full_name="Admin", password=VALID_PASSWORD)
        organization = Organization.objects.create(name="Secretaria Aprovadora")
        registration = RegistrationRequest.objects.get(user__email="aprovar@instituicao.example")
        review_registration_request(registration.pk, admin, "approve", organization_id=organization.pk)
        response = self.google_as("aprovar@instituicao.example", "sub-aprovar")
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
        user = User.objects.get(email="aprovar@instituicao.example")
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertEqual(user.organization, organization)

    def test_existing_accounts_ignore_policy(self):
        # O usuário existente da base (fora da política) continua no fluxo de vínculo da Sprint 25.
        response, _ = self.callback()
        self.assertRedirects(response, reverse("accounts:google_confirm_link"), fetch_redirect_response=False)
