"""Define uma senha temporária para uma conta da demo (Sprint 26).

Uso exclusivo pelo fluxo manual do GitHub, com confirmação. A senha vem de um
segredo (``DEMO_TEMP_PASSWORD``), nunca de entrada visível; a pessoa é obrigada
a trocar a senha no primeiro acesso. Não altera perfil, organização, status
nem permissões. O evento fica na auditoria.
"""

import os

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AuthenticationEvent, DemoProfileSwitchTarget, User
from accounts.services import clear_login_failures, record_authentication_event


class Command(BaseCommand):
    help = "Define senha temporária (troca obrigatória no próximo acesso) para uma conta da demo."

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Operação recusada: comando exclusivo do ambiente demo.")
        email = os.getenv("DEMO_RESET_EMAIL", "").strip()
        password = os.getenv("DEMO_TEMP_PASSWORD", "")
        if not email or not password:
            raise CommandError("Defina DEMO_RESET_EMAIL e o segredo DEMO_TEMP_PASSWORD.")
        user = User.objects.filter(
            email=User.objects.normalize_login_email(email), archived_at__isnull=True
        ).first()
        if user is None:
            raise CommandError("Operação recusada: conta não encontrada.")
        if DemoProfileSwitchTarget.objects.filter(user=user, is_internal=True).exists():
            raise CommandError(
                "Operação recusada: conta interna de perfil não pode receber senha."
            )
        try:
            validate_password(password, user=user)
        except ValidationError as error:
            raise CommandError("Senha temporária recusada pelas regras de senha: " + " ".join(error.messages))
        with transaction.atomic():
            user.set_password(password)
            user.must_change_password = True
            user.save(update_fields=("password", "must_change_password"))
            clear_login_failures(user.email)
            record_authentication_event(
                AuthenticationEvent.EventType.PASSWORD_CHANGED,
                user=user,
                email=user.email,
                details={"origem": "fluxo_manual_senha_temporaria", "troca_obrigatoria": True},
            )
        self.stdout.write(self.style.SUCCESS("Senha temporária definida; troca obrigatória no próximo acesso."))
