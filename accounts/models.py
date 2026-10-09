from django.contrib.auth.models import AbstractBaseUser, Group, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.db.models.functions import Lower
from django.utils import timezone

from .constants import (
    ACCESS_GROUPS,
    ADMIN_GROUP,
    CONSULTATION_GROUP,
    FISCAL_GROUP,
)
from .managers import UserManager


class AccountStatus(models.TextChoices):
    PENDING_APPROVAL = "PENDENTE_DE_APROVACAO", "Pendente de aprovação"
    ACTIVE = "ATIVO", "Ativo"
    INACTIVE = "INATIVO", "Inativo"
    BLOCKED = "BLOQUEADO", "Bloqueado"
    REJECTED = "REJEITADO", "Rejeitado"


class UserProfile(models.TextChoices):
    ADMINISTRATOR = "ADMINISTRADOR", "Administrador"
    FISCAL = "FISCAL", "Fiscal"
    CONSULTATION = "USUARIO_CONSULTA", "Usuário de Consulta"


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField("e-mail", unique=True, max_length=254)
    full_name = models.CharField("nome completo", max_length=200)
    organization_name = models.CharField("organização informada", max_length=200, blank=True)
    sector_name = models.CharField("setor informado", max_length=200, blank=True)
    phone = models.CharField("telefone", max_length=30, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="organização",
    )
    sector = models.ForeignKey(
        "organizations.Sector",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        verbose_name="setor",
    )
    profile = models.CharField(
        "perfil", max_length=20, choices=UserProfile.choices, default=UserProfile.FISCAL
    )
    status = models.CharField(
        "status",
        max_length=30,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING_APPROVAL,
    )
    must_change_password = models.BooleanField("deve trocar a senha", default=False)
    is_active = models.BooleanField("ativo para autenticação", default=False)
    is_staff = models.BooleanField("acesso à administração técnica", default=False)
    date_joined = models.DateTimeField("data de cadastro", default=timezone.now)
    archived_at = models.DateTimeField("excluído logicamente em", null=True, blank=True, db_index=True)
    archived_by = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="archived_users",
        verbose_name="excluído logicamente por",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ("full_name", "email")
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
            models.CheckConstraint(
                condition=(
                    models.Q(archived_at__isnull=True, archived_by__isnull=True)
                    | models.Q(archived_at__isnull=False, archived_by__isnull=False)
                ),
                name="accounts_user_archive_consistent",
            ),
        ]
        permissions = [
            ("manage_users", "Pode administrar usuários"),
            ("review_registration", "Pode analisar solicitações de cadastro"),
            ("view_system_health", "Pode visualizar a saúde do sistema"),
        ]

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.email

    @property
    def is_active_administrator(self):
        return (
            self.profile == UserProfile.ADMINISTRATOR
            and self.status == AccountStatus.ACTIVE
            and self.is_active
        )

    def clean(self):
        super().clean()
        self.email = UserManager.normalize_login_email(self.email)
        self.full_name = " ".join(self.full_name.split())
        self.organization_name = " ".join(self.organization_name.split())
        self.sector_name = " ".join(self.sector_name.split())
        self.phone = " ".join(self.phone.split())
        if self.sector_id:
            if not self.organization_id:
                raise ValidationError({"organization": "O setor exige uma organização."})
            if self.sector.organization_id != self.organization_id:
                raise ValidationError({"sector": "O setor deve pertencer à organização selecionada."})
        if self.is_superuser and self.profile != UserProfile.ADMINISTRATOR:
            raise ValidationError({"profile": "Superusuário deve ser Administrador."})

    @staticmethod
    def _lock_administrator_changes():
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_xact_lock(%s)", [1100372026])

    def _would_remove_last_administrator(self):
        if not self.pk:
            return False
        previous = type(self).objects.select_for_update().get(pk=self.pk)
        if not previous.is_active_administrator or self.is_active_administrator:
            return False
        return not type(self).objects.filter(
            profile=UserProfile.ADMINISTRATOR,
            status=AccountStatus.ACTIVE,
            is_active=True,
        ).exclude(pk=self.pk).exists()

    def _sync_access_group(self):
        groups = {group.name: group for group in Group.objects.filter(name__in=ACCESS_GROUPS)}
        self.groups.remove(*groups.values())
        target = {
            UserProfile.ADMINISTRATOR: ADMIN_GROUP,
            UserProfile.FISCAL: FISCAL_GROUP,
            UserProfile.CONSULTATION: CONSULTATION_GROUP,
        }.get(self.profile)
        if target is None:
            raise RuntimeError(f"Perfil sem grupo técnico correspondente: {self.profile}")
        if target not in groups:
            raise RuntimeError(f"Grupo obrigatório ausente: {target}")
        self.groups.add(groups[target])

    def save(self, *args, **kwargs):
        self.email = UserManager.normalize_login_email(self.email)
        self.full_name = " ".join(self.full_name.split())
        self.organization_name = " ".join(self.organization_name.split())
        self.sector_name = " ".join(self.sector_name.split())
        self.phone = " ".join(self.phone.split())
        self.is_active = self.status == AccountStatus.ACTIVE
        self.is_staff = self.profile == UserProfile.ADMINISTRATOR and self.is_active
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = tuple(
                set(kwargs["update_fields"]) | {"email", "full_name", "is_active", "is_staff"}
            )
        with transaction.atomic():
            self._lock_administrator_changes()
            if self._would_remove_last_administrator():
                raise ValidationError(
                    "Não é possível remover o último Administrador ativo do sistema."
                )
            self.full_clean(exclude={"password"})
            super().save(*args, **kwargs)
            self._sync_access_group()

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            self._lock_administrator_changes()
            current = type(self).objects.select_for_update().get(pk=self.pk)
            if current.is_active_administrator and not type(self).objects.filter(
                profile=UserProfile.ADMINISTRATOR,
                status=AccountStatus.ACTIVE,
                is_active=True,
            ).exclude(pk=self.pk).exists():
                raise ValidationError(
                    "Não é possível remover o último Administrador ativo do sistema."
                )
            raise ValidationError(
                "Exclusão física de usuário é bloqueada. Use a exclusão lógica auditada."
            )


class AuthenticationEvent(models.Model):
    class EventType(models.TextChoices):
        LOGIN_SUCCESS = "LOGIN_SUCESSO", "Login realizado"
        LOGIN_FAILURE = "LOGIN_FALHA", "Falha de login"
        LOGOUT = "LOGOUT", "Logout realizado"
        PASSWORD_CHANGED = "SENHA_ALTERADA", "Senha alterada"
        ADMIN_BOOTSTRAPPED = "ADMIN_CRIADO", "Administrador inicial criado"
        REGISTRATION_REQUESTED = "CADASTRO_SOLICITADO", "Cadastro solicitado"
        REGISTRATION_APPROVED = "CADASTRO_APROVADO", "Cadastro aprovado"
        REGISTRATION_REJECTED = "CADASTRO_REJEITADO", "Cadastro rejeitado"
        REGISTRATION_ARCHIVED = "CADASTRO_ARQUIVADO", "Cadastro arquivado"
        FISCAL_CREATED = "FISCAL_CRIADO", "Fiscal criado pelo Administrador"
        ACCOUNT_STATUS_CHANGED = "CONTA_STATUS_ALTERADO", "Status da conta alterado"
        ACCOUNT_ARCHIVED = "CONTA_ARQUIVADA", "Conta excluída logicamente"
        ACCOUNT_RESTORED = "CONTA_RESTAURADA", "Conta restaurada"

    event_type = models.CharField(max_length=30, choices=EventType.choices)
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="authentication_events"
    )
    identifier_hash = models.CharField(max_length=64, blank=True)
    source_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de autenticação"
        verbose_name_plural = "eventos de autenticação"


class LoginThrottle(models.Model):
    identifier_hash = models.CharField(max_length=64, unique=True)
    failure_count = models.PositiveSmallIntegerField(default=0)
    window_started_at = models.DateTimeField(default=timezone.now)
    blocked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "controle de tentativa de login"
        verbose_name_plural = "controles de tentativas de login"


class RegistrationStatus(models.TextChoices):
    PENDING = "PENDENTE", "Pendente"
    APPROVED = "APROVADO", "Aprovado"
    REJECTED = "REJEITADO", "Rejeitado"


class RegistrationRequest(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="registration_request",
        verbose_name="usuário",
    )
    status = models.CharField(
        "status", max_length=20, choices=RegistrationStatus.choices, default=RegistrationStatus.PENDING
    )
    created_at = models.DateTimeField("solicitado em", auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField("analisado em", null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_registration_requests",
        verbose_name="analisado por",
    )
    rejection_reason = models.TextField("motivo da rejeição", blank=True)
    archived_at = models.DateTimeField("arquivada em", null=True, blank=True)
    archived_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="archived_registration_requests",
        verbose_name="arquivada por",
    )

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "solicitação de cadastro"
        verbose_name_plural = "solicitações de cadastro"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status=RegistrationStatus.PENDING,
                        reviewed_by__isnull=True,
                        reviewed_at__isnull=True,
                        rejection_reason="",
                    )
                    | models.Q(
                        status=RegistrationStatus.APPROVED,
                        reviewed_by__isnull=False,
                        reviewed_at__isnull=False,
                        rejection_reason="",
                    )
                    | (
                        models.Q(
                            status=RegistrationStatus.REJECTED,
                            reviewed_by__isnull=False,
                            reviewed_at__isnull=False,
                        )
                        & ~models.Q(rejection_reason="")
                    )
                ),
                name="accounts_registration_review_state_valid",
            )
        ]

    def __str__(self):
        return f"{self.user.email} — {self.get_status_display()}"
