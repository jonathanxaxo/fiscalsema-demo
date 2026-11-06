import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import (
    AccountStatus,
    AuthenticationEvent,
    ProfileSwitchLink,
    User,
    UserProfile,
)
from accounts.services import record_authentication_event
from organizations.models import Organization
from organizations.services import create_organization


def internal_fiscal_email(administrator_email):
    local, _, domain = administrator_email.partition("@")
    return f"{local}+fiscal@{domain}"


class Command(BaseCommand):
    help = (
        "Habilita, para uma única conta administrativa da demo, a troca de perfil "
        "para Fiscal. Cria (se necessário) a organização e a conta Fiscal vinculada, "
        "sem senha própria. É idempotente."
    )

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Operação recusada: comando exclusivo do ambiente demo.")

        email = os.getenv("DEMO_ADMIN_EMAIL", "").strip()
        organization_name = os.getenv("DEMO_SWITCH_ORGANIZATION", "SEMA").strip()
        fiscal_name = os.getenv("DEMO_SWITCH_FISCAL_NAME", "Admin").strip()
        if not email or not organization_name or not fiscal_name:
            raise CommandError(
                "Defina DEMO_ADMIN_EMAIL, DEMO_SWITCH_ORGANIZATION e DEMO_SWITCH_FISCAL_NAME."
            )

        with transaction.atomic():
            administrator = (
                User.objects.select_for_update()
                .filter(
                    email__iexact=User.objects.normalize_login_email(email),
                    profile=UserProfile.ADMINISTRATOR,
                    status=AccountStatus.ACTIVE,
                    is_active=True,
                    is_superuser=True,
                )
                .first()
            )
            if administrator is None:
                raise CommandError(
                    "Operação recusada: nenhum Administrador ativo corresponde ao e-mail informado."
                )

            existing = ProfileSwitchLink.objects.filter(administrator=administrator).first()
            if existing:
                self.stdout.write("Troca de perfil já habilitada para esta conta; nada foi alterado.")
                return
            if ProfileSwitchLink.objects.exists():
                raise CommandError(
                    "Operação recusada: a troca de perfil já pertence a outra conta."
                )

            organization = Organization.objects.filter(name__iexact=organization_name).first()
            if organization is None:
                organization = create_organization(actor=administrator, name=organization_name)
            if not organization.is_active:
                raise CommandError("Operação recusada: a organização informada está inativa.")

            fiscal_email = User.objects.normalize_login_email(
                internal_fiscal_email(administrator.email)
            )
            if User.objects.filter(email__iexact=fiscal_email).exists():
                raise CommandError(
                    "Operação recusada: já existe uma conta com o identificador interno da conta Fiscal."
                )
            fiscal = User(
                email=fiscal_email,
                full_name=fiscal_name,
                profile=UserProfile.FISCAL,
                status=AccountStatus.ACTIVE,
                is_superuser=False,
                organization=organization,
            )
            fiscal.set_unusable_password()
            fiscal.save()
            ProfileSwitchLink.objects.create(administrator=administrator, fiscal=fiscal)
            record_authentication_event(
                AuthenticationEvent.EventType.FISCAL_CREATED,
                user=fiscal,
                details={
                    "origem": "enable_demo_profile_switch",
                    "administrador_id": administrator.pk,
                    "organizacao_id": organization.pk,
                },
            )

        self.stdout.write(self.style.SUCCESS("Troca de perfil habilitada com segurança."))
