import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.db.models.functions import Lower

import accounts.managers


class Migration(migrations.Migration):
    initial = True

    dependencies = [("auth", "0012_alter_user_first_name_max_length")]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False, help_text="Designates that this user has all permissions without explicitly assigning them.", verbose_name="superuser status")),
                ("email", models.EmailField(max_length=254, unique=True, verbose_name="e-mail")),
                ("full_name", models.CharField(max_length=200, verbose_name="nome completo")),
                ("profile", models.CharField(choices=[("ADMINISTRADOR", "Administrador"), ("FISCAL", "Fiscal")], default="FISCAL", max_length=20, verbose_name="perfil")),
                ("status", models.CharField(choices=[("PENDENTE_DE_APROVACAO", "Pendente de aprovação"), ("ATIVO", "Ativo"), ("INATIVO", "Inativo"), ("BLOQUEADO", "Bloqueado"), ("REJEITADO", "Rejeitado")], default="PENDENTE_DE_APROVACAO", max_length=30, verbose_name="status")),
                ("must_change_password", models.BooleanField(default=False, verbose_name="deve trocar a senha")),
                ("is_active", models.BooleanField(default=False, verbose_name="ativo para autenticação")),
                ("is_staff", models.BooleanField(default=False, verbose_name="acesso à administração técnica")),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="data de cadastro")),
                ("groups", models.ManyToManyField(blank=True, help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.", related_name="user_set", related_query_name="user", to="auth.group", verbose_name="groups")),
                ("user_permissions", models.ManyToManyField(blank=True, help_text="Specific permissions for this user.", related_name="user_set", related_query_name="user", to="auth.permission", verbose_name="user permissions")),
            ],
            options={
                "verbose_name": "usuário",
                "verbose_name_plural": "usuários",
                "ordering": ("full_name", "email"),
                "permissions": [("manage_users", "Pode administrar usuários"), ("review_registration", "Pode analisar solicitações de cadastro"), ("view_system_health", "Pode visualizar a saúde do sistema")],
                "constraints": [models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique")],
            },
            managers=[("objects", accounts.managers.UserManager())],
        ),
        migrations.CreateModel(
            name="LoginThrottle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("identifier_hash", models.CharField(max_length=64, unique=True)),
                ("failure_count", models.PositiveSmallIntegerField(default=0)),
                ("window_started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("blocked_until", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "controle de tentativa de login", "verbose_name_plural": "controles de tentativas de login"},
        ),
        migrations.CreateModel(
            name="AuthenticationEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("LOGIN_SUCESSO", "Login realizado"), ("LOGIN_FALHA", "Falha de login"), ("LOGOUT", "Logout realizado"), ("SENHA_ALTERADA", "Senha alterada"), ("ADMIN_CRIADO", "Administrador inicial criado")], max_length=30)),
                ("identifier_hash", models.CharField(blank=True, max_length=64)),
                ("source_hash", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="authentication_events", to="accounts.user")),
            ],
            options={"verbose_name": "evento de autenticação", "verbose_name_plural": "eventos de autenticação", "ordering": ("-created_at", "-pk")},
        ),
    ]
