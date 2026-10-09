from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime

from accounts.models import User
from api_v1.services import create_api_credential
from api_v1.models import ApiCredential


class Command(BaseCommand):
    help = "Cria uma credencial técnica READ_ONLY e exibe o token uma única vez."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--authorized-email", required=True)
        parser.add_argument("--created-by-email", required=True)
        parser.add_argument("--expires-at")
        parser.add_argument(
            "--mode", choices=ApiCredential.AccessMode.values,
            default=ApiCredential.AccessMode.READ_ONLY,
        )

    def handle(self, *args, **options):
        try:
            authorized_user = User.objects.get(email__iexact=options["authorized_email"])
            actor = User.objects.get(email__iexact=options["created_by_email"])
        except User.DoesNotExist as exc:
            raise CommandError("Usuário informado não foi encontrado.") from exc
        expires_at = None
        if options.get("expires_at"):
            expires_at = parse_datetime(options["expires_at"])
            if expires_at is None:
                raise CommandError("Use data/hora ISO 8601 válida em --expires-at.")
        credential, raw_token = create_api_credential(
            name=options["name"], authorized_user=authorized_user,
            actor=actor, expires_at=expires_at, access_mode=options["mode"],
        )
        self.stdout.write(self.style.WARNING("Guarde o token agora; ele não será exibido novamente."))
        self.stdout.write(f"ID: {credential.pk}")
        self.stdout.write(f"Token: {raw_token}")
