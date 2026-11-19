import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import (
    ADMINISTRATOR_PROFILES,
    FISCAL_TITULAR_PROFILES,
    AccountStatus,
    ProfileSwitchLink,
    User,
)


def _active_accounts():
    return User.objects.filter(status=AccountStatus.ACTIVE, is_active=True)


class Command(BaseCommand):
    help = (
        "Habilita, para uma única conta Fiscal da demo, a troca de perfil para o "
        "Administrador existente. Não cria contas nem altera senhas. É idempotente."
    )

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Operação recusada: comando exclusivo do ambiente demo.")

        fiscal_email = os.getenv("DEMO_SWITCH_FISCAL_EMAIL", "").strip()
        admin_email = os.getenv("DEMO_SWITCH_ADMIN_EMAIL", "").strip()
        if not fiscal_email:
            raise CommandError("Defina DEMO_SWITCH_FISCAL_EMAIL.")

        with transaction.atomic():
            fiscal = (
                _active_accounts()
                .select_for_update()
                .filter(
                    email__iexact=User.objects.normalize_login_email(fiscal_email),
                    profile__in=FISCAL_TITULAR_PROFILES,
                    is_superuser=False,
                )
                .first()
            )
            if fiscal is None:
                raise CommandError(
                    "Operação recusada: nenhuma conta Fiscal ativa corresponde ao e-mail informado."
                )

            administrators = _active_accounts().filter(
                profile__in=ADMINISTRATOR_PROFILES, is_superuser=True
            )
            if admin_email:
                administrators = administrators.filter(
                    email__iexact=User.objects.normalize_login_email(admin_email)
                )
            administrators = list(administrators.select_for_update()[:2])
            if len(administrators) != 1:
                raise CommandError(
                    "Operação recusada: é preciso existir exatamente um Administrador ativo "
                    "(ou informar o e-mail de um Administrador ativo)."
                )
            administrator = administrators[0]

            existing = ProfileSwitchLink.objects.filter(fiscal=fiscal, administrator=administrator)
            if existing.exists():
                self.stdout.write("Troca de perfil já habilitada para esta conta; nada foi alterado.")
                return
            if ProfileSwitchLink.objects.exists():
                raise CommandError("Operação recusada: a troca de perfil já pertence a outra conta.")

            ProfileSwitchLink.objects.create(administrator=administrator, fiscal=fiscal)

        self.stdout.write(self.style.SUCCESS("Troca de perfil habilitada com segurança."))
