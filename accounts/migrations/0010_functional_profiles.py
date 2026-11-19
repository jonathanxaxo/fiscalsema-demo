from django.db import migrations, models


NEW_GROUPS = (
    "ADMINISTRADOR_GERAL",
    "FISCAL_TITULAR",
    "AUXILIAR_ADMINISTRATIVA",
    "GESTOR_ADMINISTRATIVO",
    "GESTOR_DO_CONTRATO",
    "USUARIO_DE_CONSULTA",
)


def migrate_profiles_forward(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    RegistrationRequest = apps.get_model("accounts", "RegistrationRequest")
    Group = apps.get_model("auth", "Group")

    groups = {name: Group.objects.get_or_create(name=name)[0] for name in NEW_GROUPS}
    old_admin = Group.objects.filter(name="ADMINISTRADOR").first()
    old_fiscal = Group.objects.filter(name="FISCAL").first()
    if old_admin:
        groups["ADMINISTRADOR_GERAL"].permissions.add(*old_admin.permissions.all())
    if old_fiscal:
        groups["FISCAL_TITULAR"].permissions.add(*old_fiscal.permissions.all())

    User.objects.filter(profile="ADMINISTRADOR").update(profile="ADMINISTRADOR_GERAL")
    User.objects.filter(profile="FISCAL").update(profile="FISCAL_TITULAR")

    access_names = set(NEW_GROUPS) | {"ADMINISTRADOR", "FISCAL"}
    for user in User.objects.all().iterator():
        user.groups.remove(*Group.objects.filter(name__in=access_names))
        target = {
            "ADMINISTRADOR_GERAL": "ADMINISTRADOR_GERAL",
            "FISCAL_TITULAR": "FISCAL_TITULAR",
            "AUXILIAR_ADMINISTRATIVA": "AUXILIAR_ADMINISTRATIVA",
            "GESTOR_ADMINISTRATIVO": "GESTOR_ADMINISTRATIVO",
            "GESTOR_DO_CONTRATO": "GESTOR_DO_CONTRATO",
            "USUARIO_CONSULTA": "USUARIO_DE_CONSULTA",
        }.get(user.profile)
        if target:
            user.groups.add(groups[target])

    for registration in RegistrationRequest.objects.select_related("user").iterator():
        registration.requested_profile = registration.user.profile
        registration.save(update_fields=("requested_profile",))


def migrate_profiles_backward(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    RegistrationRequest = apps.get_model("accounts", "RegistrationRequest")
    Group = apps.get_model("auth", "Group")

    old_admin = Group.objects.get_or_create(name="ADMINISTRADOR")[0]
    old_fiscal = Group.objects.get_or_create(name="FISCAL")[0]
    consultation = Group.objects.get_or_create(name="USUARIO_DE_CONSULTA")[0]
    User.objects.filter(profile="ADMINISTRADOR_GERAL").update(profile="ADMINISTRADOR")
    User.objects.filter(profile="FISCAL_TITULAR").update(profile="FISCAL")
    User.objects.filter(
        profile__in=(
            "AUXILIAR_ADMINISTRATIVA",
            "GESTOR_ADMINISTRATIVO",
            "GESTOR_DO_CONTRATO",
        )
    ).update(profile="USUARIO_CONSULTA")
    RegistrationRequest.objects.filter(requested_profile="ADMINISTRADOR_GERAL").update(
        requested_profile="ADMINISTRADOR"
    )
    RegistrationRequest.objects.filter(requested_profile="FISCAL_TITULAR").update(
        requested_profile="FISCAL"
    )
    RegistrationRequest.objects.filter(
        requested_profile__in=(
            "AUXILIAR_ADMINISTRATIVA",
            "GESTOR_ADMINISTRATIVO",
            "GESTOR_DO_CONTRATO",
        )
    ).update(requested_profile="USUARIO_CONSULTA")
    for user in User.objects.all().iterator():
        user.groups.remove(*Group.objects.filter(name__in=NEW_GROUPS))
        if user.profile == "ADMINISTRADOR":
            user.groups.add(old_admin)
        elif user.profile == "FISCAL":
            user.groups.add(old_fiscal)
        elif user.profile == "USUARIO_CONSULTA":
            user.groups.add(consultation)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0009_google_identity")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="profile",
            field=models.CharField(
                choices=[
                    ("ADMINISTRADOR_GERAL", "Administrador Geral"),
                    ("FISCAL_TITULAR", "Fiscal Titular"),
                    ("AUXILIAR_ADMINISTRATIVA", "Auxiliar Administrativa"),
                    ("GESTOR_ADMINISTRATIVO", "Gestor Administrativo"),
                    ("GESTOR_DO_CONTRATO", "Gestor do Contrato"),
                    ("ADMINISTRADOR", "Administrador (legado)"),
                    ("FISCAL", "Fiscal (legado)"),
                    ("USUARIO_CONSULTA", "Usuário de Consulta (legado)"),
                ],
                default="FISCAL_TITULAR",
                max_length=30,
                verbose_name="perfil",
            ),
        ),
        migrations.AddField(
            model_name="registrationrequest",
            name="requested_profile",
            field=models.CharField(
                choices=[
                    ("ADMINISTRADOR_GERAL", "Administrador Geral"),
                    ("FISCAL_TITULAR", "Fiscal Titular"),
                    ("AUXILIAR_ADMINISTRATIVA", "Auxiliar Administrativa"),
                    ("GESTOR_ADMINISTRATIVO", "Gestor Administrativo"),
                    ("GESTOR_DO_CONTRATO", "Gestor do Contrato"),
                    ("ADMINISTRADOR", "Administrador (legado)"),
                    ("FISCAL", "Fiscal (legado)"),
                    ("USUARIO_CONSULTA", "Usuário de Consulta (legado)"),
                ],
                default="FISCAL_TITULAR",
                max_length=30,
                verbose_name="perfil solicitado",
            ),
        ),
        migrations.AddField(
            model_name="registrationrequest",
            name="justification",
            field=models.TextField(blank=True, verbose_name="justificativa"),
        ),
        migrations.RunPython(migrate_profiles_forward, migrate_profiles_backward),
    ]
