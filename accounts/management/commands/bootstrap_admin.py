import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AccountStatus, AuthenticationEvent, User, UserProfile
from accounts.services import record_authentication_event


class Command(BaseCommand):
    help = "Cria interativamente o primeiro Administrador local."

    def add_arguments(self, parser):
        parser.add_argument("--email")
        parser.add_argument("--full-name")

    def handle(self, *args, **options):
        if User.objects.filter(
            profile=UserProfile.ADMINISTRATOR_GENERAL,
            status=AccountStatus.ACTIVE,
            is_active=True,
        ).exists():
            raise CommandError("Já existe Administrador ativo; bootstrap recusado.")

        email = options.get("email") or input("E-mail do Administrador: ").strip()
        full_name = options.get("full_name") or input("Nome completo: ").strip()
        password = getpass.getpass("Senha: ")
        confirmation = getpass.getpass("Confirme a senha: ")
        if password != confirmation:
            raise CommandError("A confirmação da senha não confere.")

        candidate = User(
            email=User.objects.normalize_login_email(email),
            full_name=full_name,
            profile=UserProfile.ADMINISTRATOR_GENERAL,
            status=AccountStatus.ACTIVE,
            is_superuser=True,
        )
        validate_password(password, user=candidate)

        with transaction.atomic():
            user = User.objects.create_superuser(
                email=email,
                full_name=full_name,
                password=password,
            )
            record_authentication_event(
                AuthenticationEvent.EventType.ADMIN_BOOTSTRAPPED,
                user=user,
                email=user.email,
                details={"origem": "comando_interativo"},
            )
        self.stdout.write(self.style.SUCCESS("Administrador local criado com segurança."))
