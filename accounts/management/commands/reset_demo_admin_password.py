import os

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AccountStatus, AuthenticationEvent, User, UserProfile
from accounts.services import record_authentication_event


class Command(BaseCommand):
    help = (
        "Redefine a senha do Administrador do ambiente demo a partir de "
        "variáveis de ambiente. Não cria contas e não altera o login."
    )

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Redefinição recusada: comando exclusivo do ambiente demo.")

        email = os.getenv("DEMO_ADMIN_EMAIL", "").strip()
        password = os.getenv("DEMO_ADMIN_PASSWORD", "")
        if not email or not password:
            raise CommandError("Defina DEMO_ADMIN_EMAIL e DEMO_ADMIN_PASSWORD.")

        with transaction.atomic():
            user = (
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
            if user is None:
                raise CommandError(
                    "Redefinição recusada: nenhum Administrador ativo corresponde ao e-mail informado."
                )

            validate_password(password, user=user)
            user.set_password(password)
            user.must_change_password = False
            user.save(update_fields=("password", "must_change_password"))
            record_authentication_event(
                AuthenticationEvent.EventType.PASSWORD_CHANGED,
                user=user,
                details={"origem": "reset_demo_admin_password_env"},
            )

        self.stdout.write(self.style.SUCCESS("Senha do Administrador demo redefinida com segurança."))
