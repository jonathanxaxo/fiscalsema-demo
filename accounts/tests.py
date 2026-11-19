from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from organizations.models import Organization, OrganizationEvent, Sector

from .constants import ADMIN_GROUP, CONSULTATION_GROUP, FISCAL_GROUP
from .models import (
    AccountStatus,
    AuthenticationEvent,
    LoginThrottle,
    RegistrationRequest,
    RegistrationStatus,
    UserProfile,
)


User = get_user_model()
VALID_PASSWORD = "SenhaMuitoForte!2026"
OTHER_VALID_PASSWORD = "OutraSenhaForte!2027"


class AdministrativeUserLifecycleTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin.ciclo@example.local",
            full_name="Administrador do Ciclo",
            password=VALID_PASSWORD,
        )
        self.fiscal = User.objects.create_user(
            email="fiscal.ciclo@example.local",
            full_name="Fiscal do Ciclo",
            password=OTHER_VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
        )
        self.client.force_login(self.admin)

    def test_list_exposes_safe_lifecycle_actions(self):
        response = self.client.get(reverse("accounts_admin:user_list"))
        self.assertContains(response, "Inativar")
        self.assertContains(response, "Ver contas excluídas")
        self.assertContains(response, "Conta em uso")

    def test_administrator_inactivates_and_reactivates_other_user(self):
        fiscal_client = Client()
        fiscal_client.force_login(self.fiscal)
        old_session_key = fiscal_client.session.session_key

        response = self.client.post(
            reverse(
                "accounts_admin:user_status",
                args=[self.fiscal.pk, "deactivate"],
            )
        )
        self.assertRedirects(response, reverse("accounts_admin:user_list"))
        self.fiscal.refresh_from_db()
        self.assertEqual(self.fiscal.status, AccountStatus.INACTIVE)
        self.assertFalse(self.fiscal.is_active)
        self.assertFalse(Session.objects.filter(session_key=old_session_key).exists())
        self.assertTrue(
            AuthenticationEvent.objects.filter(
                event_type=AuthenticationEvent.EventType.ACCOUNT_STATUS_CHANGED,
                user=self.fiscal,
                details__status_novo=AccountStatus.INACTIVE,
            ).exists()
        )

        self.client.post(
            reverse(
                "accounts_admin:user_status",
                args=[self.fiscal.pk, "activate"],
            )
        )
        self.fiscal.refresh_from_db()
        self.assertEqual(self.fiscal.status, AccountStatus.ACTIVE)
        self.assertTrue(self.fiscal.is_active)

    def test_logical_delete_requires_inactive_and_preserves_history(self):
        response = self.client.post(
            reverse("accounts_admin:user_archive", args=[self.fiscal.pk]),
            follow=True,
        )
        self.assertContains(response, "Inative a conta antes", status_code=200)
        self.fiscal.refresh_from_db()
        self.assertIsNone(self.fiscal.archived_at)

        self.client.post(
            reverse("accounts_admin:user_status", args=[self.fiscal.pk, "deactivate"])
        )
        self.client.post(reverse("accounts_admin:user_archive", args=[self.fiscal.pk]))
        self.fiscal.refresh_from_db()
        self.assertIsNotNone(self.fiscal.archived_at)
        self.assertEqual(self.fiscal.archived_by, self.admin)
        self.assertEqual(self.fiscal.status, AccountStatus.INACTIVE)
        self.assertTrue(
            User.objects.filter(pk=self.fiscal.pk, archived_at__isnull=False).exists()
        )
        self.assertTrue(
            AuthenticationEvent.objects.filter(
                event_type=AuthenticationEvent.EventType.ACCOUNT_ARCHIVED,
                user=self.fiscal,
            ).exists()
        )
        self.assertNotContains(
            self.client.get(reverse("accounts_admin:user_list")), self.fiscal.email
        )
        archived_list = self.client.get(
            f"{reverse('accounts_admin:user_list')}?excluidos=1"
        )
        self.assertContains(archived_list, self.fiscal.email)
        self.assertContains(archived_list, "Restaurar")

    def test_restore_keeps_user_inactive_until_explicit_activation(self):
        self.client.post(
            reverse("accounts_admin:user_status", args=[self.fiscal.pk, "deactivate"])
        )
        self.client.post(reverse("accounts_admin:user_archive", args=[self.fiscal.pk]))
        response = self.client.post(
            reverse("accounts_admin:user_restore", args=[self.fiscal.pk])
        )
        self.assertRedirects(
            response,
            f"{reverse('accounts_admin:user_list')}?excluidos=1",
        )
        self.fiscal.refresh_from_db()
        self.assertIsNone(self.fiscal.archived_at)
        self.assertIsNone(self.fiscal.archived_by)
        self.assertEqual(self.fiscal.status, AccountStatus.INACTIVE)
        self.assertFalse(self.fiscal.is_active)
        self.assertTrue(
            AuthenticationEvent.objects.filter(
                event_type=AuthenticationEvent.EventType.ACCOUNT_RESTORED,
                user=self.fiscal,
            ).exists()
        )

    def test_administrator_cannot_change_or_archive_own_account(self):
        self.client.post(
            reverse("accounts_admin:user_status", args=[self.admin.pk, "deactivate"])
        )
        self.client.post(reverse("accounts_admin:user_archive", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active_administrator)
        self.assertIsNone(self.admin.archived_at)

    def test_user_without_administrative_permission_cannot_mutate_accounts(self):
        self.client.force_login(self.fiscal)
        response = self.client.post(
            reverse("accounts_admin:user_archive", args=[self.admin.pk])
        )
        self.assertEqual(response.status_code, 403)


class UserIdentityTests(TestCase):
    def test_email_is_normalized_and_unique_ignoring_case(self):
        user = User.objects.create_user(
            email="  Fiscal.Teste@EXAMPLE.LOCAL ",
            full_name="  Fiscal   de Teste  ",
            password=VALID_PASSWORD,
        )
        self.assertEqual(user.email, "fiscal.teste@example.local")
        self.assertEqual(user.full_name, "Fiscal de Teste")
        with self.assertRaises(ValidationError):
            User.objects.create_user(
                email="FISCAL.TESTE@example.local",
                full_name="Outra Pessoa",
                password=OTHER_VALID_PASSWORD,
            )

    def test_password_is_hashed(self):
        user = User.objects.create_user(
            email="hash@example.local",
            full_name="Teste Hash",
            password=VALID_PASSWORD,
        )
        self.assertNotEqual(user.password, VALID_PASSWORD)
        self.assertTrue(user.check_password(VALID_PASSWORD))

    def test_password_policy_rejects_each_missing_requirement(self):
        user = User(email="fiscal@example.local", full_name="Fiscal")
        invalid_passwords = (
            "Aa1!x",
            "senhamuitoforte!2026",
            "SENHAMUITOFORTE!2026",
            "SenhaMuitoForteSemNumero!",
            "SenhaMuitoForte2026SemEspecial",
            "fiscal@example.local",
        )
        for password in invalid_passwords:
            with self.subTest(password=password), self.assertRaises(ValidationError):
                validate_password(password, user=user)
        validate_password(VALID_PASSWORD, user=user)

    def test_password_policy_accepts_six_and_rejects_more_than_twenty_four(self):
        user = User(email="limite@example.local", full_name="Teste Limite")
        validate_password("Aa1!xy", user=user)
        with self.assertRaises(ValidationError):
            validate_password("Aa1!" + "x" * 21, user=user)

    def test_new_regular_user_is_pending_fiscal_and_grouped(self):
        user = User.objects.create_user(
            email="pending@example.local",
            full_name="Fiscal Pendente",
            password=VALID_PASSWORD,
        )
        self.assertEqual(user.status, AccountStatus.PENDING_APPROVAL)
        self.assertEqual(user.profile, UserProfile.FISCAL_TITULAR)
        self.assertFalse(user.is_active)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), [FISCAL_GROUP])


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="fiscal@example.local",
            full_name="Fiscal Ativo",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
        )
        self.client = Client()

    def test_active_user_logs_in_by_normalized_email(self):
        session_before = self.client.session.session_key
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "FISCAL@EXAMPLE.LOCAL", "password": VALID_PASSWORD},
        )
        self.assertRedirects(response, reverse("home"))
        self.assertNotEqual(self.client.session.session_key, session_before)
        self.assertTrue(response.cookies["fiscalsema_sessionid"]["httponly"])
        self.assertEqual(response.cookies["fiscalsema_sessionid"]["samesite"], "Lax")
        self.assertTrue(AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.LOGIN_SUCCESS,
            user=self.user,
        ).exists())

    def test_non_active_states_cannot_authenticate(self):
        for status in (
            AccountStatus.PENDING_APPROVAL,
            AccountStatus.INACTIVE,
            AccountStatus.BLOCKED,
            AccountStatus.REJECTED,
        ):
            self.user.status = status
            self.user.save()
            response = self.client.post(
                reverse("accounts:login"),
                {"username": self.user.email, "password": VALID_PASSWORD},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "E-mail ou senha inválidos.")
            self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(
            AuthenticationEvent.objects.filter(
                event_type=AuthenticationEvent.EventType.LOGIN_FAILURE
            ).count(),
            4,
        )

    @override_settings(AUTH_LOGIN_MAX_FAILURES=3)
    def test_brute_force_throttle_blocks_even_correct_password(self):
        url = reverse("accounts:login")
        for _ in range(3):
            self.client.post(url, {"username": self.user.email, "password": "Errada!2026"})
        throttle = LoginThrottle.objects.get()
        self.assertIsNotNone(throttle.blocked_until)
        response = self.client.post(
            url, {"username": self.user.email, "password": VALID_PASSWORD}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post_and_is_audited(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertTrue(AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.LOGOUT,
            user=self.user,
        ).exists())

    def test_forced_password_change_blocks_normal_area(self):
        self.user.must_change_password = True
        self.user.save()
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(reverse("home")), reverse("accounts:password_change"))
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": VALID_PASSWORD,
                "new_password1": OTHER_VALID_PASSWORD,
                "new_password2": OTHER_VALID_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(self.user.check_password(OTHER_VALID_PASSWORD))
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_response_is_generic(self):
        from django.core import mail

        response_existing = self.client.post(
            reverse("accounts:password_reset"), {"email": self.user.email}
        )
        response_missing = self.client.post(
            reverse("accounts:password_reset"), {"email": "ausente@example.local"}
        )
        self.assertEqual(response_existing.status_code, response_missing.status_code)
        self.assertEqual(response_existing.url, response_missing.url)
        self.assertEqual(len(mail.outbox), 1)


class ProfileAndAdministratorProtectionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin@example.local",
            full_name="Administrador Local",
            password=VALID_PASSWORD,
        )

    def test_profiles_have_exactly_one_access_group(self):
        fiscal = User.objects.create_user(
            email="fiscal.grupo@example.local",
            full_name="Fiscal Grupo",
            password=VALID_PASSWORD,
        )
        consultation = User.objects.create_user(
            email="consulta.grupo@example.local",
            full_name="Usuário de Consulta",
            password=VALID_PASSWORD,
            profile=UserProfile.CONSULTATION,
        )
        self.assertEqual(set(self.admin.groups.values_list("name", flat=True)), {ADMIN_GROUP})
        self.assertEqual(set(fiscal.groups.values_list("name", flat=True)), {FISCAL_GROUP})
        self.assertEqual(
            set(consultation.groups.values_list("name", flat=True)),
            {CONSULTATION_GROUP},
        )
        self.assertTrue(Group.objects.get(name=ADMIN_GROUP).permissions.filter(
            codename="manage_users"
        ).exists())
        self.assertFalse(consultation.has_perm("accounts.manage_users"))
        self.assertFalse(consultation.has_perm("accounts.review_registration"))

    def test_consultation_profile_is_never_staff_or_active_fiscal(self):
        consultation = User.objects.create_user(
            email="consulta.ativa@example.local",
            full_name="Consulta Ativa",
            password=VALID_PASSWORD,
            profile=UserProfile.CONSULTATION,
            status=AccountStatus.ACTIVE,
        )
        self.assertTrue(consultation.is_active)
        self.assertFalse(consultation.is_staff)
        self.assertFalse(consultation.is_superuser)

    def test_last_active_administrator_cannot_be_inactivated_demoted_or_deleted(self):
        for field, value in (
            ("status", AccountStatus.INACTIVE),
            ("profile", UserProfile.FISCAL),
        ):
            admin = User.objects.get(pk=self.admin.pk)
            setattr(admin, field, value)
            if field == "profile":
                admin.is_superuser = False
            with self.assertRaisesMessage(
                ValidationError,
                "Não é possível remover o último Administrador ativo do sistema.",
            ):
                admin.save()
        with self.assertRaisesMessage(
            ValidationError,
            "Não é possível remover o último Administrador ativo do sistema.",
        ):
            self.admin.delete()

    def test_administrator_can_change_when_another_active_one_exists(self):
        User.objects.create_superuser(
            email="admin2@example.local",
            full_name="Segundo Administrador",
            password=OTHER_VALID_PASSWORD,
        )
        self.admin.is_superuser = False
        self.admin.profile = UserProfile.FISCAL
        self.admin.save()
        self.assertEqual(self.admin.profile, UserProfile.FISCAL)

    def test_physical_delete_is_blocked_even_with_another_administrator(self):
        User.objects.create_superuser(
            email="admin3@example.local",
            full_name="Terceiro Administrador",
            password=OTHER_VALID_PASSWORD,
        )
        with self.assertRaisesMessage(
            ValidationError,
            "Exclusão física de usuário é bloqueada",
        ):
            self.admin.delete()


class BootstrapAdministratorCommandTests(TestCase):
    def test_bootstrap_is_interactive_audited_and_single_use(self):
        with patch(
            "accounts.management.commands.bootstrap_admin.getpass.getpass",
            side_effect=[VALID_PASSWORD, VALID_PASSWORD],
        ):
            call_command(
                "bootstrap_admin",
                email="admin.bootstrap@example.local",
                full_name="Administrador Bootstrap",
                verbosity=0,
            )
        user = User.objects.get(email="admin.bootstrap@example.local")
        self.assertTrue(user.is_active_administrator)
        self.assertTrue(user.is_superuser)
        self.assertTrue(AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.ADMIN_BOOTSTRAPPED,
            user=user,
        ).exists())
        with self.assertRaisesMessage(CommandError, "Já existe Administrador ativo"):
            call_command(
                "bootstrap_admin",
                email="outro@example.local",
                full_name="Outro Admin",
                verbosity=0,
            )


class FiscalRegistrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.registration_data = {
            "full_name": "  Fiscal   Novo  ",
            "email": " Fiscal.Novo@EXAMPLE.LOCAL ",
            "organization_name": "  DEMO   MT  ",
            "sector_name": "  Unidade   Técnica  ",
            "phone": " (65)  99999-0000 ",
            "requested_profile": UserProfile.FISCAL_TITULAR,
            "justification": "Atuar na fiscalização de contratos demonstrativos.",
            "password1": VALID_PASSWORD,
            "password2": VALID_PASSWORD,
        }

    def test_public_registration_creates_pending_fiscal_request_and_audit(self):
        response = self.client.post(reverse("accounts:register"), self.registration_data)
        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        user = User.objects.get(email="fiscal.novo@example.local")
        self.assertEqual(user.full_name, "Fiscal Novo")
        self.assertEqual(user.organization_name, "DEMO MT")
        self.assertEqual(user.sector_name, "Unidade Técnica")
        self.assertEqual(user.phone, "(65) 99999-0000")
        self.assertEqual(user.profile, UserProfile.FISCAL_TITULAR)
        self.assertEqual(user.status, AccountStatus.PENDING_APPROVAL)
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password(VALID_PASSWORD))
        self.assertEqual(user.registration_request.status, RegistrationStatus.PENDING)
        self.assertTrue(
            AuthenticationEvent.objects.filter(
                event_type=AuthenticationEvent.EventType.REGISTRATION_REQUESTED,
                user=user,
            ).exists()
        )

    def test_registration_exposes_password_limits_and_current_profile_choices(self):
        response = self.client.get(reverse("accounts:register"))
        form = response.context["form"]
        self.assertEqual(form.fields["password1"].widget.attrs["minlength"], 6)
        self.assertEqual(form.fields["password1"].widget.attrs["maxlength"], 24)
        choices = {value for value, _label in form.fields["requested_profile"].choices}
        self.assertIn(UserProfile.FISCAL_TITULAR, choices)
        self.assertNotIn(UserProfile.ADMINISTRATOR_GENERAL, choices)
        self.assertNotIn(UserProfile.CONSULTATION, choices)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(
            email="fiscal.novo@example.local",
            full_name="Já Existe",
            password=OTHER_VALID_PASSWORD,
        )
        response = self.client.post(reverse("accounts:register"), self.registration_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Já existe uma conta com este e-mail.")
        self.assertEqual(User.objects.filter(email__iexact="fiscal.novo@example.local").count(), 1)
        self.assertEqual(RegistrationRequest.objects.count(), 0)

    def test_organization_is_required_and_sector_is_optional(self):
        data = self.registration_data.copy()
        data["organization_name"] = ""
        self.assertContains(self.client.post(reverse("accounts:register"), data), "Este campo é obrigatório")
        data["organization_name"] = "DEMO"
        data["sector_name"] = ""
        response = self.client.post(reverse("accounts:register"), data)
        self.assertRedirects(response, reverse("accounts:registration_submitted"))
        self.assertEqual(User.objects.get().sector_name, "")

    def test_pending_fiscal_cannot_login(self):
        self.client.post(reverse("accounts:register"), self.registration_data)
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "fiscal.novo@example.local", "password": VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class RegistrationAdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email="admin.cadastro@example.local",
            full_name="Administrador Cadastro",
            password=VALID_PASSWORD,
        )
        self.organization = Organization.objects.create(
            name="DEMO", created_by=self.admin
        )
        self.sector = Sector.objects.create(
            organization=self.organization,
            name="Unidade Técnica",
            created_by=self.admin,
        )
        self.fiscal = User.objects.create_user(
            email="pendente@example.local",
            full_name="Fiscal Pendente",
            organization_name="DEMO",
            password=OTHER_VALID_PASSWORD,
        )
        self.registration = RegistrationRequest.objects.create(user=self.fiscal)

    def test_administrator_lists_and_approves_request_then_login_is_allowed(self):
        self.client.force_login(self.admin)
        list_response = self.client.get(reverse("accounts_admin:registration_list"))
        self.assertContains(list_response, self.fiscal.email)
        response = self.client.post(
            reverse("accounts_admin:registration_review", args=[self.registration.pk]),
            {
                "action": "approve",
                "rejection_reason": "",
                "organization": self.organization.pk,
                "sector": self.sector.pk,
                "approved_profile": UserProfile.FISCAL_TITULAR,
            },
        )
        self.assertRedirects(response, reverse("accounts_admin:registration_list"))
        self.registration.refresh_from_db()
        self.fiscal.refresh_from_db()
        self.assertEqual(self.registration.status, RegistrationStatus.APPROVED)
        self.assertEqual(self.registration.reviewed_by, self.admin)
        self.assertIsNotNone(self.registration.reviewed_at)
        self.assertEqual(self.fiscal.status, AccountStatus.ACTIVE)
        self.assertEqual(self.fiscal.organization, self.organization)
        self.assertEqual(self.fiscal.sector, self.sector)
        self.assertTrue(self.fiscal.is_active)
        self.assertTrue(AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.REGISTRATION_APPROVED,
            user=self.fiscal,
        ).exists())
        self.assertTrue(OrganizationEvent.objects.filter(
            event_type=OrganizationEvent.EventType.USER_ASSIGNED,
            user=self.fiscal,
            organization=self.organization,
            sector=self.sector,
        ).exists())
        self.client.logout()
        self.assertRedirects(
            self.client.post(
                reverse("accounts:login"),
                {"username": self.fiscal.email, "password": OTHER_VALID_PASSWORD},
            ),
            reverse("home"),
        )

    def test_rejection_requires_reason_and_records_decision(self):
        self.client.force_login(self.admin)
        url = reverse("accounts_admin:registration_review", args=[self.registration.pk])
        response = self.client.post(url, {"action": "reject", "rejection_reason": ""})
        self.assertEqual(response.status_code, 200)
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, RegistrationStatus.PENDING)
        response = self.client.post(
            url,
            {"action": "reject", "rejection_reason": "Vínculo institucional não confirmado."},
        )
        self.assertRedirects(response, reverse("accounts_admin:registration_list"))
        self.registration.refresh_from_db()
        self.fiscal.refresh_from_db()
        self.assertEqual(self.registration.status, RegistrationStatus.REJECTED)
        self.assertEqual(self.registration.rejection_reason, "Vínculo institucional não confirmado.")
        self.assertEqual(self.fiscal.status, AccountStatus.REJECTED)
        self.assertFalse(self.fiscal.is_active)
        self.assertTrue(AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.REGISTRATION_REJECTED,
            user=self.fiscal,
        ).exists())

    def test_analyzed_request_cannot_be_reviewed_twice(self):
        self.client.force_login(self.admin)
        url = reverse("accounts_admin:registration_review", args=[self.registration.pk])
        approval = {
            "action": "approve",
            "rejection_reason": "",
            "organization": self.organization.pk,
            "sector": self.sector.pk,
            "approved_profile": UserProfile.FISCAL_TITULAR,
        }
        self.client.post(url, approval)
        response = self.client.post(url, approval)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Esta solicitação já foi analisada.")
        self.assertEqual(AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.REGISTRATION_APPROVED,
            user=self.fiscal,
        ).count(), 1)

    def test_administrator_archives_request_without_deleting_history(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts_admin:registration_archive", args=[self.registration.pk])
        )
        self.assertRedirects(response, reverse("accounts_admin:registration_list"))
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.archived_by, self.admin)
        self.assertIsNotNone(self.registration.archived_at)
        self.assertTrue(RegistrationRequest.objects.filter(pk=self.registration.pk).exists())
        self.assertNotContains(
            self.client.get(reverse("accounts_admin:registration_list")), self.fiscal.email
        )
        self.assertContains(
            self.client.get(
                reverse("accounts_admin:registration_list") + "?status=PENDENTE&arquivadas=1"
            ),
            self.fiscal.email,
        )
        self.assertTrue(
            AuthenticationEvent.objects.filter(
                event_type=AuthenticationEvent.EventType.REGISTRATION_ARCHIVED,
                user=self.fiscal,
            ).exists()
        )

    def test_common_fiscal_cannot_access_administration_by_direct_url(self):
        other = User.objects.create_user(
            email="fiscal.ativo@example.local",
            full_name="Fiscal Ativo",
            password=VALID_PASSWORD,
            status=AccountStatus.ACTIVE,
        )
        self.client.force_login(other)
        self.assertNotContains(self.client.get(reverse("home")), "Solicitações de cadastro")
        urls = (
            reverse("accounts_admin:registration_list"),
            reverse("accounts_admin:registration_review", args=[self.registration.pk]),
            reverse("accounts_admin:registration_archive", args=[self.registration.pk]),
            reverse("accounts_admin:fiscal_create"),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_administrator_sees_administration_links(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Solicitações de cadastro")
        self.assertContains(response, "Criar usuário")

    def test_django_admin_cannot_bypass_audited_creation_flow(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:accounts_user_add")).status_code, 403)

    def test_administrator_creates_active_fiscal_without_request_and_forces_password_change(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts_admin:fiscal_create"),
            {
                "full_name": "Fiscal Administrativo",
                "email": "fiscal.admin@example.local",
                "organization": self.organization.pk,
                "sector": self.sector.pk,
                "phone": "",
                "profile": UserProfile.FISCAL_TITULAR,
                "password1": OTHER_VALID_PASSWORD,
                "password2": OTHER_VALID_PASSWORD,
            },
        )
        self.assertRedirects(response, reverse("accounts_admin:fiscal_create"))
        user = User.objects.get(email="fiscal.admin@example.local")
        self.assertEqual(user.status, AccountStatus.ACTIVE)
        self.assertTrue(user.is_active)
        self.assertTrue(user.must_change_password)
        self.assertEqual(user.organization, self.organization)
        self.assertEqual(user.sector, self.sector)
        self.assertFalse(RegistrationRequest.objects.filter(user=user).exists())
        self.assertTrue(AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.USER_CREATED,
            user=user,
        ).exists())
        self.client.logout()
        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": OTHER_VALID_PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))
        self.assertRedirects(self.client.get(reverse("home")), reverse("accounts:password_change"))

    def test_approval_requires_structured_organization(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts_admin:registration_review", args=[self.registration.pk]),
            {
                "action": "approve",
                "rejection_reason": "",
                "organization": "",
                "sector": "",
                "approved_profile": UserProfile.FISCAL_TITULAR,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecione a organização da pessoa usuária.")
        self.registration.refresh_from_db()
        self.fiscal.refresh_from_db()
        self.assertEqual(self.registration.status, RegistrationStatus.PENDING)
        self.assertEqual(self.fiscal.status, AccountStatus.PENDING_APPROVAL)

    def test_sector_from_other_organization_is_rejected(self):
        other_organization = Organization.objects.create(name="Outra Organização")
        other_sector = Sector.objects.create(
            organization=other_organization, name="Outro Setor"
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts_admin:registration_review", args=[self.registration.pk]),
            {
                "action": "approve",
                "rejection_reason": "",
                "organization": self.organization.pk,
                "sector": other_sector.pk,
                "approved_profile": UserProfile.FISCAL_TITULAR,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O setor deve pertencer à organização selecionada.")
