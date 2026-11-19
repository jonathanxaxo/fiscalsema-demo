from django.contrib.auth.models import AbstractBaseUser, Group, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import connection, models, transaction
from django.db.models.functions import Lower
from django.utils import timezone

from .constants import (
    ACCESS_GROUPS,
    ADMINISTRATIVE_MANAGER_GROUP,
    ADMINISTRATOR_GENERAL_GROUP,
    AUXILIARY_ADMINISTRATIVE_GROUP,
    CONTRACT_MANAGER_GROUP,
    FISCAL_TITULAR_GROUP,
    LEGACY_CONSULTATION_GROUP,
)
from .managers import UserManager


class AccountStatus(models.TextChoices):
    PENDING_APPROVAL = "PENDENTE_DE_APROVACAO", "Pendente de aprovação"
    ACTIVE = "ATIVO", "Ativo"
    INACTIVE = "INATIVO", "Inativo"
    BLOCKED = "BLOQUEADO", "Bloqueado"
    REJECTED = "REJEITADO", "Rejeitado"


class UserProfile(models.TextChoices):
    ADMINISTRATOR_GENERAL = "ADMINISTRADOR_GERAL", "Administrador Geral"
    FISCAL_TITULAR = "FISCAL_TITULAR", "Fiscal Titular"
    AUXILIARY_ADMINISTRATIVE = "AUXILIAR_ADMINISTRATIVA", "Auxiliar Administrativa"
    ADMINISTRATIVE_MANAGER = "GESTOR_ADMINISTRATIVO", "Gestor Administrativo"
    CONTRACT_MANAGER = "GESTOR_DO_CONTRATO", "Gestor do Contrato"

    # Valores transitórios: permanecem reconhecidos até a migration e a
    # classificação humana das contas de consulta existentes.
    ADMINISTRATOR = "ADMINISTRADOR", "Administrador (legado)"
    FISCAL = "FISCAL", "Fiscal (legado)"
    CONSULTATION = "USUARIO_CONSULTA", "Usuário de Consulta (legado)"


ADMINISTRATOR_PROFILES = (
    UserProfile.ADMINISTRATOR_GENERAL,
    UserProfile.ADMINISTRATOR,
)
FISCAL_TITULAR_PROFILES = (
    UserProfile.FISCAL_TITULAR,
    UserProfile.FISCAL,
)
REGISTRATION_PROFILE_CHOICES = (
    (UserProfile.FISCAL_TITULAR, UserProfile.FISCAL_TITULAR.label),
    (UserProfile.AUXILIARY_ADMINISTRATIVE, UserProfile.AUXILIARY_ADMINISTRATIVE.label),
    (UserProfile.ADMINISTRATIVE_MANAGER, UserProfile.ADMINISTRATIVE_MANAGER.label),
    (UserProfile.CONTRACT_MANAGER, UserProfile.CONTRACT_MANAGER.label),
)

DEMO_SWITCH_PROFILE_CHOICES = (
    (UserProfile.ADMINISTRATOR_GENERAL, UserProfile.ADMINISTRATOR_GENERAL.label),
    (UserProfile.FISCAL_TITULAR, UserProfile.FISCAL_TITULAR.label),
    (UserProfile.AUXILIARY_ADMINISTRATIVE, UserProfile.AUXILIARY_ADMINISTRATIVE.label),
    (UserProfile.ADMINISTRATIVE_MANAGER, UserProfile.ADMINISTRATIVE_MANAGER.label),
    (UserProfile.CONTRACT_MANAGER, UserProfile.CONTRACT_MANAGER.label),
)
DEMO_SWITCH_PROFILES = tuple(value for value, _label in DEMO_SWITCH_PROFILE_CHOICES)


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
        "perfil",
        max_length=30,
        choices=UserProfile.choices,
        default=UserProfile.FISCAL_TITULAR,
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
            self.profile in ADMINISTRATOR_PROFILES
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
        if self.is_superuser and self.profile not in ADMINISTRATOR_PROFILES:
            raise ValidationError({"profile": "Superusuário deve ser Administrador Geral."})

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
            profile__in=ADMINISTRATOR_PROFILES,
            status=AccountStatus.ACTIVE,
            is_active=True,
        ).exclude(pk=self.pk).exists()

    def _sync_access_group(self):
        groups = {group.name: group for group in Group.objects.filter(name__in=ACCESS_GROUPS)}
        self.groups.remove(*groups.values())
        target = {
            UserProfile.ADMINISTRATOR_GENERAL: ADMINISTRATOR_GENERAL_GROUP,
            UserProfile.FISCAL_TITULAR: FISCAL_TITULAR_GROUP,
            UserProfile.AUXILIARY_ADMINISTRATIVE: AUXILIARY_ADMINISTRATIVE_GROUP,
            UserProfile.ADMINISTRATIVE_MANAGER: ADMINISTRATIVE_MANAGER_GROUP,
            UserProfile.CONTRACT_MANAGER: CONTRACT_MANAGER_GROUP,
            UserProfile.ADMINISTRATOR: ADMINISTRATOR_GENERAL_GROUP,
            UserProfile.FISCAL: FISCAL_TITULAR_GROUP,
            UserProfile.CONSULTATION: LEGACY_CONSULTATION_GROUP,
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
        self.is_staff = self.profile in ADMINISTRATOR_PROFILES and self.is_active
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
                profile__in=ADMINISTRATOR_PROFILES,
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
        USER_CREATED = "USUARIO_CRIADO", "Usuário criado pelo Administrador"
        PROFILE_CHANGED = "PERFIL_ALTERADO", "Perfil alterado pelo Administrador"
        ACCOUNT_STATUS_CHANGED = "CONTA_STATUS_ALTERADO", "Status da conta alterado"
        ACCOUNT_ARCHIVED = "CONTA_ARQUIVADA", "Conta excluída logicamente"
        ACCOUNT_RESTORED = "CONTA_RESTAURADA", "Conta restaurada"
        PROFILE_SWITCHED_TO_FISCAL = "PERFIL_FISCAL", "Perfil alternado para Fiscal"
        PROFILE_SWITCHED_TO_ADMIN = "PERFIL_ADMIN", "Perfil alternado para Administrador"
        PROFILE_SWITCHED = "PERFIL_ALTERNADO", "Perfil de demonstração alternado"
        GOOGLE_LOGIN = "LOGIN_GOOGLE", "Login com Google"
        GOOGLE_LOGIN_DENIED = "LOGIN_GOOGLE_NEGADO", "Login com Google recusado"
        GOOGLE_LINKED = "GOOGLE_VINCULADO", "Conta Google vinculada"
        GOOGLE_UNLINKED = "GOOGLE_DESVINCULADO", "Conta Google desvinculada"

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
    requested_profile = models.CharField(
        "perfil solicitado",
        max_length=30,
        choices=UserProfile.choices,
        default=UserProfile.FISCAL_TITULAR,
    )
    justification = models.TextField("justificativa", blank=True)
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


class ProfileSwitchLink(models.Model):
    """Exceção da demo: uma conta administrativa que pode atuar como Fiscal.

    O vínculo só é criado por comando de gestão (fluxo manual auditado); não
    existe tela para concedê-lo.
    """

    administrator = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="profile_switch_link",
        verbose_name="administrador",
    )
    fiscal = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="profile_switch_owner",
        verbose_name="conta fiscal vinculada",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "vínculo de troca de perfil"
        verbose_name_plural = "vínculos de troca de perfil"

    def clean(self):
        super().clean()
        if self.administrator_id == self.fiscal_id:
            raise ValidationError("O vínculo exige duas contas distintas.")
        if not (
            self.administrator.is_superuser
            and self.administrator.profile in ADMINISTRATOR_PROFILES
        ):
            raise ValidationError({"administrator": "A conta de origem deve ser Administrador Geral."})
        if self.fiscal.profile not in FISCAL_TITULAR_PROFILES or self.fiscal.is_superuser:
            raise ValidationError({"fiscal": "A conta vinculada deve ser Fiscal Titular."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DemoProfileSwitch(models.Model):
    """Exceção da demo: uma única conta controla perfis internos de apresentação."""

    controller = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="demo_profile_switch",
        verbose_name="conta controladora",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "troca multiperfil da demonstração"
        verbose_name_plural = "trocas multiperfil da demonstração"

    def __str__(self):
        return f"Troca multiperfil — {self.controller.email}"


class DemoProfileSwitchTarget(models.Model):
    """Conta que materializa as permissões reais de um perfil na demonstração."""

    switch = models.ForeignKey(
        DemoProfileSwitch,
        on_delete=models.CASCADE,
        related_name="targets",
        verbose_name="troca multiperfil",
    )
    profile = models.CharField(
        "perfil",
        max_length=30,
        choices=DEMO_SWITCH_PROFILE_CHOICES,
    )
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        related_name="demo_profile_target",
        verbose_name="conta do perfil",
    )
    is_internal = models.BooleanField("conta interna sem login direto", default=False)
    created_at = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        ordering = ("profile", "pk")
        verbose_name = "perfil disponível na demonstração"
        verbose_name_plural = "perfis disponíveis na demonstração"
        constraints = [
            models.UniqueConstraint(
                fields=("switch", "profile"),
                name="accounts_demo_switch_profile_unique",
            )
        ]

    def clean(self):
        super().clean()
        if self.profile not in DEMO_SWITCH_PROFILES:
            raise ValidationError({"profile": "Selecione um perfil funcional atual."})
        if self.user_id and self.user.profile != self.profile:
            raise ValidationError(
                {"user": "A conta interna deve possuir o mesmo perfil do vínculo."}
            )
        if self.is_internal and self.user_id and self.user.has_usable_password():
            raise ValidationError(
                {"user": "Conta interna de perfil não pode aceitar login por senha."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_profile_display()} — {self.switch.controller.email}"


class ExternalIdentity(models.Model):
    """Identidade de um provedor externo (Sprint 25: Google) vinculada a um usuário.

    O vínculo não altera nada no cadastro do usuário (nome, perfil,
    organização, permissões ou senha). O identificador do provedor (``sub``)
    é único: uma identidade Google aponta para um único usuário.
    """

    class Provider(models.TextChoices):
        GOOGLE = "google", "Google"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="external_identities",
        verbose_name="usuário",
    )
    provider = models.CharField("provedor", max_length=20, choices=Provider.choices)
    subject = models.CharField("identificador no provedor", max_length=255)
    email = models.EmailField("e-mail no provedor", max_length=254)
    linked_at = models.DateTimeField("vinculada em", auto_now_add=True)
    last_login_at = models.DateTimeField("último login", null=True, blank=True)

    class Meta:
        ordering = ("provider", "linked_at")
        verbose_name = "identidade externa"
        verbose_name_plural = "identidades externas"
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "subject"), name="accounts_external_identity_unique_subject"
            ),
        ]

    def __str__(self):
        return f"{self.get_provider_display()} — {self.email}"
