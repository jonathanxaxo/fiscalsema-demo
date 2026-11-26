"""Sprint 75: autocadastro com órgão/setor e senha criada pelo link do e-mail."""

import re
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from contracts.models import Contract, ContractAccess, ContractAccessType, ContractSharingEvent
from contracts.services import contracts_visible_to, contracts_writable_by
from contracts.tests import VALID_PASSWORD, contract_data
from organizations.models import Organization, OrganizationEvent, Sector

from .models import AccountStatus, AuthenticationEvent, User, UserProfile

NOVA_SENHA = "NovaSenha!2026"


@override_settings(SELF_SIGNUP_ENABLED=True, SELF_SIGNUP_LIMIT_PER_HOUR=50)
class AutocadastroTests(TestCase):
    def setUp(self):
        self.orgao = Organization.objects.create(name="SEMA Demonstração")
        self.setor = Sector.objects.create(organization=self.orgao, name="Coordenadoria Fictícia")
        self.fiscal_demo = User.objects.create_user(
            email="fiscal.demo@example.local", full_name="Fiscal Demo", password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE, organization=self.orgao,
        )
        self.contrato_demo = Contract.objects.create(
            **contract_data(number="DEMO-0001-01/2026", notes="[DEMO-CARTEIRA] [DEMO-APRESENTACAO] Uso exclusivo em demonstração."),
            contracting_organization=self.orgao, responsible_fiscal=self.fiscal_demo,
        )
        self.contrato_real = Contract.objects.create(
            **contract_data(number="OUTRO-01/2026"), contracting_organization=self.orgao, responsible_fiscal=self.fiscal_demo,
        )
        self.url = reverse("accounts:self_signup")

    def cadastrar(self, email="nova.pessoa@gmail.com", **extra):
        dados = {"full_name": "Nova Pessoa", "email": email, "organization": self.orgao.pk, "sector": self.setor.pk}
        dados.update(extra)
        return self.client.post(self.url, {k: v for k, v in dados.items() if v is not None})

    def link_do_email(self):
        return re.search(r"https?://[^\s]+/conta/criar-senha/[^\s]+/", mail.outbox[-1].body).group(0)

    # ---------- tela e configuração ----------
    def test_login_shows_create_account_button(self):
        self.assertContains(self.client.get(reverse("accounts:login")), reverse("accounts:self_signup"))

    @override_settings(SELF_SIGNUP_ENABLED=False)
    def test_disabled_returns_404_and_hides_button(self):
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertNotContains(self.client.get(reverse("accounts:login")), "Criar conta")

    def test_form_lists_existing_organizations_and_sectors(self):
        response = self.client.get(self.url)
        self.assertContains(response, "SEMA Demonstração")
        self.assertContains(response, "SEMA Demonstração — Coordenadoria Fictícia")

    # ---------- cadastro ----------
    def test_signup_with_existing_organization_creates_active_fiscal_without_password(self):
        response = self.cadastrar()
        self.assertRedirects(response, reverse("accounts:self_signup_sent"))
        user = User.objects.get(email="nova.pessoa@gmail.com")
        self.assertEqual(user.status, AccountStatus.ACTIVE)
        self.assertEqual(user.profile, UserProfile.FISCAL_TITULAR)
        self.assertFalse(user.has_usable_password())
        self.assertEqual((user.organization, user.sector), (self.orgao, self.setor))
        evento = AuthenticationEvent.objects.get(user=user, event_type=AuthenticationEvent.EventType.REGISTRATION_REQUESTED)
        self.assertTrue(evento.details["autocadastro"])

    def test_email_has_single_use_link_and_never_a_password(self):
        self.cadastrar()
        self.assertEqual(len(mail.outbox), 1)
        mensagem = mail.outbox[0]
        self.assertEqual(mensagem.to, ["nova.pessoa@gmail.com"])
        self.assertIn("Crie sua senha", mensagem.subject)
        self.assertIn("/conta/criar-senha/", mensagem.body)
        self.assertNotIn("senha provisória", mensagem.body.lower())

    def test_new_organization_and_sector_are_created_and_listed_for_next_person(self):
        self.cadastrar(organization=None, sector=None, new_organization="Secretaria Fictícia de Teste", new_sector="Núcleo Novo")
        orgao = Organization.objects.get(name="Secretaria Fictícia de Teste")
        setor = Sector.objects.get(organization=orgao, name="Núcleo Novo")
        self.assertTrue(OrganizationEvent.objects.filter(organization=orgao, event_type=OrganizationEvent.EventType.ORGANIZATION_CREATED).exists())
        self.assertTrue(OrganizationEvent.objects.filter(sector=setor, event_type=OrganizationEvent.EventType.SECTOR_CREATED).exists())
        self.assertContains(self.client.get(self.url), "Secretaria Fictícia de Teste — Núcleo Novo")
        self.cadastrar(email="segunda@gmail.com", organization=orgao.pk, sector=setor.pk)
        self.assertEqual(User.objects.get(email="segunda@gmail.com").sector, setor)

    def test_typed_name_reuses_existing_organization_and_sector_without_duplicates(self):
        self.cadastrar(organization=None, sector=None, new_organization="  sema   DEMONSTRAÇÃO ", new_sector="coordenadoria fictícia")
        self.assertEqual(Organization.objects.filter(name__iexact="SEMA Demonstração").count(), 1)
        self.assertEqual(Sector.objects.filter(organization=self.orgao).count(), 1)
        self.assertEqual(User.objects.get(email="nova.pessoa@gmail.com").sector, self.setor)

    def test_choice_rules_are_validated(self):
        outro = Organization.objects.create(name="Outro Órgão")
        casos = [
            {"organization": self.orgao.pk, "new_organization": "Duplicado"},
            {"organization": None},
            {"organization": outro.pk},
            {"organization": None, "new_organization": "Órgão Novo"},
            {"sector": None},
        ]
        for extra in casos:
            with self.subTest(extra=extra):
                response = self.cadastrar(**extra)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(User.objects.filter(email="nova.pessoa@gmail.com").exists())

    def test_inactive_organization_cannot_be_reused_by_name(self):
        Organization.objects.create(name="Órgão Desativado", is_active=False)
        response = self.cadastrar(organization=None, sector=None, new_organization="órgão desativado", new_sector="Setor X")
        self.assertContains(response, "não está disponível")
        self.assertFalse(User.objects.filter(email="nova.pessoa@gmail.com").exists())

    # ---------- acesso aos contratos ----------
    def test_only_demo_contracts_are_shared_read_only(self):
        self.cadastrar()
        user = User.objects.get(email="nova.pessoa@gmail.com")
        acessos = ContractAccess.objects.filter(user=user)
        self.assertEqual(list(acessos.values_list("contract_id", flat=True)), [self.contrato_demo.pk])
        self.assertEqual(acessos.get().access_type, ContractAccessType.READ_ONLY)
        self.assertEqual(acessos.get().granted_by, self.fiscal_demo)
        self.assertTrue(ContractSharingEvent.objects.filter(access=acessos.get(), details__origem="autocadastro").exists())
        user.set_password(NOVA_SENHA); user.save()
        self.assertIn(self.contrato_demo, contracts_visible_to(user))
        self.assertNotIn(self.contrato_real, contracts_visible_to(user))
        self.assertNotIn(self.contrato_demo, contracts_writable_by(user))

    # ---------- senha pelo link ----------
    def test_password_created_by_link_then_link_is_used_up(self):
        self.cadastrar()
        link = self.link_do_email()
        formulario = self.client.get(link, follow=True)
        self.assertContains(formulario, "Criar sua senha")
        destino = formulario.redirect_chain[-1][0]
        resposta = self.client.post(destino, {"new_password1": NOVA_SENHA, "new_password2": NOVA_SENHA}, follow=True)
        self.assertContains(resposta, "Senha criada")
        user = User.objects.get(email="nova.pessoa@gmail.com")
        self.assertTrue(user.check_password(NOVA_SENHA))
        self.assertTrue(AuthenticationEvent.objects.filter(user=user, event_type=AuthenticationEvent.EventType.PASSWORD_CHANGED, details__origem="autocadastro").exists())
        self.client.logout()
        self.assertContains(self.client.get(link, follow=True), "inválido, expirou ou já foi utilizado")
        self.assertTrue(self.client.login(username="nova.pessoa@gmail.com", password=NOVA_SENHA))

    def test_signup_again_before_password_resends_link(self):
        self.cadastrar()
        self.cadastrar()
        self.assertEqual(User.objects.filter(email="nova.pessoa@gmail.com").count(), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_existing_account_with_password_is_refused(self):
        response = self.cadastrar(email="fiscal.demo@example.local")
        self.assertContains(response, "Já existe uma conta com este e-mail")
        self.assertEqual(len(mail.outbox), 0)

    # ---------- proteções ----------
    @override_settings(SELF_SIGNUP_LIMIT_PER_HOUR=2)
    def test_rate_limit_per_connection(self):
        self.cadastrar(email="a@gmail.com")
        self.cadastrar(email="b@gmail.com")
        response = self.cadastrar(email="c@gmail.com")
        self.assertContains(response, "Muitos cadastros")
        self.assertFalse(User.objects.filter(email="c@gmail.com").exists())

    def test_hidden_field_blocks_robots(self):
        response = self.cadastrar(website="http://spam.invalid")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email="nova.pessoa@gmail.com").exists())

    def test_email_failure_keeps_account_and_offers_resend(self):
        with mock.patch("accounts.autocadastro.send_mail", side_effect=OSError("smtp fora")):
            self.assertRedirects(self.cadastrar(), reverse("accounts:self_signup_sent"), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(email="nova.pessoa@gmail.com").exists())
        self.assertContains(self.client.get(reverse("accounts:self_signup_sent")), "o e-mail não pôde ser enviado agora")
        # Com o e-mail de volta, o mesmo cadastro reenvia o link.
        self.cadastrar()
        self.assertEqual(len(mail.outbox), 1)
