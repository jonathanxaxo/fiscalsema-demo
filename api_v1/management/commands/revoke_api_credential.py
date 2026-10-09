from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from api_v1.models import ApiCredential
from api_v1.services import revoke_api_credential


class Command(BaseCommand):
    help = "Revoga imediatamente uma credencial da API."

    def add_arguments(self, parser):
        parser.add_argument("credential_id", type=int)
        parser.add_argument("--revoked-by-email", required=True)

    def handle(self, *args, **options):
        try:
            credential = ApiCredential.objects.get(pk=options["credential_id"])
            actor = User.objects.get(email__iexact=options["revoked_by_email"])
        except (ApiCredential.DoesNotExist, User.DoesNotExist) as exc:
            raise CommandError("Credencial ou Administrador não encontrado.") from exc
        revoke_api_credential(credential=credential, actor=actor)
        self.stdout.write(self.style.SUCCESS("Credencial revogada."))
