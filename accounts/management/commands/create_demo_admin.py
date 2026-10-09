import os

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AuthenticationEvent, User
from accounts.services import record_authentication_event


class Command(BaseCommand):
    help = "Cria a única conta administrativa inicial do ambiente demo."

    def handle(self, *args, **options):
        if User.objects.exists():
            raise CommandError(
                "Criação recusada: o banco demo já possui uma conta."
            )

        email = os.getenv("DEMO_ADMIN_EMAIL", "").strip()
        password = os.getenv("DEMO_ADMIN_PASSWORD", "")
        full_name = os.getenv("DEMO_ADMIN_NAME", "Administrador Demonstração").strip()
        if not email or not password or not full_name:
            raise CommandError(
                "Defina DEMO_ADMIN_EMAIL, DEMO_ADMIN_PASSWORD e DEMO_ADMIN_NAME."
            )

        candidate = User(email=User.objects.normalize_login_email(email), full_name=full_name)
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
                details={"origem": "create_demo_admin_env"},
            )
        self.stdout.write(self.style.SUCCESS("Administrador demo criado com segurança."))
