import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.demo_profiles import configure_all_demo_profiles
from accounts.models import User


class Command(BaseCommand):
    help = (
        "Habilita uma única conta da demo para alternar entre os cinco perfis "
        "sem alterar sua senha ou o cadastro das demais contas."
    )

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Operação recusada: comando exclusivo do ambiente demo.")
        email = os.getenv("DEMO_SWITCH_CONTROLLER_EMAIL", "").strip()
        if not email:
            raise CommandError("Defina DEMO_SWITCH_CONTROLLER_EMAIL.")

        with transaction.atomic():
            controller = (
                User.objects.select_for_update()
                .filter(email__iexact=User.objects.normalize_login_email(email))
                .first()
            )
            if controller is None:
                raise CommandError("Operação recusada: conta controladora não encontrada.")
            try:
                switch, created_internal = configure_all_demo_profiles(
                    controller=controller
                )
            except ValidationError as error:
                raise CommandError(" ".join(error.messages)) from error

        self.stdout.write(
            self.style.SUCCESS(
                "Troca multiperfil habilitada com segurança: "
                f"{switch.targets.count()} perfis, "
                f"{len(created_internal)} conta(s) interna(s) criada(s)."
            )
        )
