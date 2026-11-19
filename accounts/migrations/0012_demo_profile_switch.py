from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


CURRENT_PROFILES = {
    "ADMINISTRADOR_GERAL",
    "FISCAL_TITULAR",
    "AUXILIAR_ADMINISTRATIVA",
    "GESTOR_ADMINISTRATIVO",
    "GESTOR_DO_CONTRATO",
}


def migrate_existing_switch(apps, schema_editor):
    ProfileSwitchLink = apps.get_model("accounts", "ProfileSwitchLink")
    DemoProfileSwitch = apps.get_model("accounts", "DemoProfileSwitch")
    DemoProfileSwitchTarget = apps.get_model("accounts", "DemoProfileSwitchTarget")

    for link in ProfileSwitchLink.objects.select_related("administrator", "fiscal"):
        switch, _created = DemoProfileSwitch.objects.get_or_create(controller=link.fiscal)
        for user in (link.fiscal, link.administrator):
            if user.profile in CURRENT_PROFILES:
                DemoProfileSwitchTarget.objects.get_or_create(
                    switch=switch,
                    profile=user.profile,
                    defaults={"user": user, "is_internal": False},
                )


def remove_migrated_switch(apps, schema_editor):
    DemoProfileSwitch = apps.get_model("accounts", "DemoProfileSwitch")
    DemoProfileSwitch.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_alter_authenticationevent_event_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="DemoProfileSwitch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                (
                    "controller",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="demo_profile_switch",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="conta controladora",
                    ),
                ),
            ],
            options={
                "verbose_name": "troca multiperfil da demonstração",
                "verbose_name_plural": "trocas multiperfil da demonstração",
            },
        ),
        migrations.CreateModel(
            name="DemoProfileSwitchTarget",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "profile",
                    models.CharField(
                        choices=[
                            ("ADMINISTRADOR_GERAL", "Administrador Geral"),
                            ("FISCAL_TITULAR", "Fiscal Titular"),
                            ("AUXILIAR_ADMINISTRATIVA", "Auxiliar Administrativa"),
                            ("GESTOR_ADMINISTRATIVO", "Gestor Administrativo"),
                            ("GESTOR_DO_CONTRATO", "Gestor do Contrato"),
                        ],
                        max_length=30,
                        verbose_name="perfil",
                    ),
                ),
                (
                    "is_internal",
                    models.BooleanField(
                        default=False,
                        verbose_name="conta interna sem login direto",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="criado em")),
                (
                    "switch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="targets",
                        to="accounts.demoprofileswitch",
                        verbose_name="troca multiperfil",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="demo_profile_target",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="conta do perfil",
                    ),
                ),
            ],
            options={
                "verbose_name": "perfil disponível na demonstração",
                "verbose_name_plural": "perfis disponíveis na demonstração",
                "ordering": ("profile", "pk"),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("switch", "profile"),
                        name="accounts_demo_switch_profile_unique",
                    )
                ],
            },
        ),
        migrations.RunPython(migrate_existing_switch, remove_migrated_switch),
        migrations.AlterField(
            model_name="authenticationevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("LOGIN_SUCESSO", "Login realizado"),
                    ("LOGIN_FALHA", "Falha de login"),
                    ("LOGOUT", "Logout realizado"),
                    ("SENHA_ALTERADA", "Senha alterada"),
                    ("ADMIN_CRIADO", "Administrador inicial criado"),
                    ("CADASTRO_SOLICITADO", "Cadastro solicitado"),
                    ("CADASTRO_APROVADO", "Cadastro aprovado"),
                    ("CADASTRO_REJEITADO", "Cadastro rejeitado"),
                    ("CADASTRO_ARQUIVADO", "Cadastro arquivado"),
                    ("FISCAL_CRIADO", "Fiscal criado pelo Administrador"),
                    ("USUARIO_CRIADO", "Usuário criado pelo Administrador"),
                    ("PERFIL_ALTERADO", "Perfil alterado pelo Administrador"),
                    ("CONTA_STATUS_ALTERADO", "Status da conta alterado"),
                    ("CONTA_ARQUIVADA", "Conta excluída logicamente"),
                    ("CONTA_RESTAURADA", "Conta restaurada"),
                    ("PERFIL_FISCAL", "Perfil alternado para Fiscal"),
                    ("PERFIL_ADMIN", "Perfil alternado para Administrador"),
                    ("PERFIL_ALTERNADO", "Perfil de demonstração alternado"),
                    ("LOGIN_GOOGLE", "Login com Google"),
                    ("LOGIN_GOOGLE_NEGADO", "Login com Google recusado"),
                    ("GOOGLE_VINCULADO", "Conta Google vinculada"),
                    ("GOOGLE_DESVINCULADO", "Conta Google desvinculada"),
                ],
                max_length=30,
            ),
        ),
    ]
