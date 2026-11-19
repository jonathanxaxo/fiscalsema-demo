from django.core.management.base import BaseCommand
from django.db.models import Count

from accounts.models import User, UserProfile


class Command(BaseCommand):
    help = (
        "Inventaria perfis funcionais sem alterar contas. Use antes da migração "
        "ou publicação para identificar contas legadas que exigem decisão humana."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--details",
            action="store_true",
            help="Lista ID, e-mail fictício, status e organização das contas legadas.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Inventário somente leitura de perfis funcionais")
        regular_users = User.objects.exclude(demo_profile_target__is_internal=True)
        counts = {
            row["profile"]: row["total"]
            for row in regular_users.values("profile")
            .annotate(total=Count("pk"))
            .order_by("profile")
        }
        for value, label in UserProfile.choices:
            total = counts.get(value, 0)
            if total:
                self.stdout.write(f"- {value} ({label}): {total}")

        internal_count = User.objects.filter(
            demo_profile_target__is_internal=True
        ).count()
        if internal_count:
            self.stdout.write(
                f"Contas internas da demonstração (sem login direto): {internal_count}"
            )

        legacy = regular_users.filter(profile=UserProfile.CONSULTATION).select_related(
            "organization"
        ).order_by("pk")
        self.stdout.write(f"USUARIO_CONSULTA a reclassificar: {legacy.count()}")
        self.stdout.write(
            "Destino automático: nenhum. O Administrador Geral deve escolher "
            "Auxiliar Administrativa, Gestor Administrativo, Gestor do Contrato "
            "ou outro perfil atual para cada conta."
        )
        if options["details"]:
            for user in legacy:
                organization = (
                    user.organization.name
                    if user.organization_id
                    else "sem organização"
                )
                self.stdout.write(
                    f"  id={user.pk} email={user.email} status={user.status} "
                    f"organizacao={organization}"
                )
