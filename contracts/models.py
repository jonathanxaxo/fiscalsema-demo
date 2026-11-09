from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from accounts.models import UserProfile


def normalized_text(value):
    return " ".join((value or "").split())


tax_id_validator = RegexValidator(
    regex=r"^(?:\d{11}|\d{14})$",
    message="Informe CPF com 11 dígitos ou CNPJ com 14 dígitos.",
)


class ContractStatus(models.TextChoices):
    ACTIVE = "ATIVO", "Ativo"
    SUSPENDED = "SUSPENSO", "Suspenso"
    CLOSED = "ENCERRADO", "Encerrado"
    CANCELED = "CANCELADO", "Cancelado"


class Contract(models.Model):
    number = models.CharField("número", max_length=100, db_index=True)
    process_number = models.CharField("processo", max_length=100, db_index=True)
    object = models.TextField("objeto")
    contracting_organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="contracts",
        verbose_name="contratante",
    )
    supplier_name = models.CharField("fornecedor", max_length=200)
    supplier_tax_id = models.CharField(
        "CNPJ/CPF do fornecedor",
        max_length=14,
        validators=(tax_id_validator,),
    )
    signature_date = models.DateField("data de assinatura")
    validity_start = models.DateField("início da vigência")
    validity_end = models.DateField("fim da vigência")
    original_value = models.DecimalField(
        "valor original",
        max_digits=20,
        decimal_places=2,
    )
    status = models.CharField(
        "status",
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.ACTIVE,
        db_index=True,
    )
    responsible_fiscal = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="responsible_contracts",
        verbose_name="Fiscal responsável",
    )
    notes = models.TextField("observações", blank=True)
    closed_at = models.DateTimeField("encerrado em", null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contracts_closed",
        verbose_name="encerrado por",
    )
    closure_reason = models.TextField("justificativa do encerramento", blank=True)
    archived_at = models.DateTimeField(
        "arquivado logicamente em", null=True, blank=True, db_index=True
    )
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contracts_archived",
        verbose_name="arquivado logicamente por",
    )
    archive_reason = models.TextField("justificativa do arquivamento", blank=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        ordering = ("number", "pk")
        verbose_name = "contrato"
        verbose_name_plural = "contratos"
        permissions = [("view_all_contracts", "Pode consultar todos os contratos")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(original_value__gte=Decimal("0.00")),
                name="contracts_original_value_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(validity_end__gte=models.F("validity_start")),
                name="contracts_validity_order",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        archived_at__isnull=True,
                        archived_by__isnull=True,
                        archive_reason="",
                    )
                    | (
                        models.Q(archived_at__isnull=False, archived_by__isnull=False)
                        & ~models.Q(archive_reason="")
                    )
                ),
                name="contracts_archive_consistent",
            ),
        ]

    @property
    def current_value(self):
        # Até a etapa de aditivos, a regra aprovada define valor atual = original.
        return self.original_value

    @property
    def calendar_year_periods(self):
        from .periods import calendar_year_periods

        return calendar_year_periods(self)

    @property
    def contract_year_periods(self):
        from .periods import contract_year_periods

        return contract_year_periods(self)

    def clean(self):
        super().clean()
        self.number = normalized_text(self.number)
        self.process_number = normalized_text(self.process_number)
        self.object = normalized_text(self.object)
        self.supplier_name = normalized_text(self.supplier_name)
        self.supplier_tax_id = "".join(
            character for character in (self.supplier_tax_id or "") if character.isdigit()
        )
        self.notes = (self.notes or "").strip()
        self.archive_reason = normalized_text(self.archive_reason)
        required = {
            "number": (self.number, "Informe o número do contrato."),
            "process_number": (self.process_number, "Informe o processo."),
            "object": (self.object, "Informe o objeto do contrato."),
            "supplier_name": (self.supplier_name, "Informe o fornecedor."),
        }
        errors = {field: message for field, (value, message) in required.items() if not value}
        if self.validity_start and self.validity_end and self.validity_end < self.validity_start:
            errors["validity_end"] = "O fim da vigência não pode anteceder o início."
        if self.original_value is not None and self.original_value < Decimal("0.00"):
            errors["original_value"] = "O valor original não pode ser negativo."
        if self.responsible_fiscal_id and self.responsible_fiscal.profile != UserProfile.FISCAL:
            errors["responsible_fiscal"] = "O responsável deve possuir perfil Fiscal."
        archived_fields_complete = bool(
            self.archived_at and self.archived_by_id and self.archive_reason
        )
        archived_fields_empty = bool(
            not self.archived_at and not self.archived_by_id and not self.archive_reason
        )
        if not archived_fields_complete and not archived_fields_empty:
            errors["archived_at"] = (
                "Arquivamento exige autor, data e justificativa; contrato ativo não pode "
                "conter esses dados."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Contrato não pode ser excluído fisicamente; use o arquivamento lógico auditado."
        )

    def __str__(self):
        return f"Contrato {self.number} — {self.supplier_name}"


class ContractAccessType(models.TextChoices):
    READ_ONLY = "READ_ONLY", "Somente leitura"


class ContractAccessStatus(models.TextChoices):
    ACTIVE = "ATIVO", "Ativo"
    REVOKED = "REVOGADO", "Revogado"


class ContractAccess(models.Model):
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="accesses",
        verbose_name="contrato",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="contract_accesses", verbose_name="usuário",
    )
    access_type = models.CharField(
        "tipo de acesso", max_length=20, choices=ContractAccessType.choices,
        default=ContractAccessType.READ_ONLY,
    )
    status = models.CharField(
        "status", max_length=20, choices=ContractAccessStatus.choices,
        default=ContractAccessStatus.ACTIVE, db_index=True,
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="contract_accesses_granted", verbose_name="concedido por",
    )
    granted_at = models.DateTimeField("concedido em", default=timezone.now)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="contract_accesses_revoked", verbose_name="revogado por",
    )
    revoked_at = models.DateTimeField("revogado em", null=True, blank=True)

    class Meta:
        ordering = ("contract", "user__full_name", "pk")
        verbose_name = "acesso ao contrato"
        verbose_name_plural = "acessos aos contratos"
        constraints = [
            models.UniqueConstraint(
                fields=("contract", "user"), name="contracts_access_contract_user_unique"
            ),
        ]

    def clean(self):
        super().clean()
        errors = {}
        if self.access_type != ContractAccessType.READ_ONLY:
            errors["access_type"] = "Somente o acesso READ_ONLY está autorizado."
        if self.status == ContractAccessStatus.ACTIVE:
            if self.revoked_by_id or self.revoked_at:
                errors["status"] = "Acesso ativo não pode conter dados de revogação."
        elif not self.revoked_by_id or not self.revoked_at:
            errors["status"] = "Acesso revogado exige autor e data da revogação."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Acesso ao contrato não pode ser excluído; use revogação.")

    def __str__(self):
        return f"{self.get_access_type_display()} — {self.user} — {self.contract}"


class ContractInvitationStatus(models.TextChoices):
    PENDING = "PENDENTE", "Pendente"
    ACCEPTED = "ACEITO", "Aceito"
    EXPIRED = "EXPIRADO", "Expirado"
    CANCELED = "CANCELADO", "Cancelado"


class ContractInvitation(models.Model):
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="invitations",
        verbose_name="contrato",
    )
    email = models.EmailField("e-mail", max_length=254, db_index=True)
    access_type = models.CharField(
        "tipo de acesso", max_length=20, choices=ContractAccessType.choices,
        default=ContractAccessType.READ_ONLY,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="contract_invitations_sent", verbose_name="convidado por",
    )
    invited_at = models.DateTimeField("convidado em", auto_now_add=True)
    expires_at = models.DateTimeField(
        "válido até", null=True, blank=True,
        help_text="Sem prazo automático até existir regra institucional comprovada.",
    )
    status = models.CharField(
        "status", max_length=20, choices=ContractInvitationStatus.choices,
        default=ContractInvitationStatus.PENDING, db_index=True,
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="contract_invitations_accepted", verbose_name="aceito por",
    )
    accepted_at = models.DateTimeField("aceito em", null=True, blank=True)

    class Meta:
        ordering = ("-invited_at", "pk")
        verbose_name = "convite de acesso ao contrato"
        verbose_name_plural = "convites de acesso aos contratos"
        constraints = [
            models.UniqueConstraint(
                fields=("contract", "email"),
                condition=models.Q(status=ContractInvitationStatus.PENDING),
                name="contracts_invitation_pending_unique",
            ),
        ]

    def clean(self):
        super().clean()
        self.email = (self.email or "").strip().casefold()
        errors = {}
        if self.access_type != ContractAccessType.READ_ONLY:
            errors["access_type"] = "Somente o acesso READ_ONLY está autorizado."
        accepted = self.status == ContractInvitationStatus.ACCEPTED
        if accepted and (not self.accepted_by_id or not self.accepted_at):
            errors["status"] = "Convite aceito exige usuário e data de aceite."
        if not accepted and (self.accepted_by_id or self.accepted_at):
            errors["status"] = "Dados de aceite exigem status Aceito."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().casefold()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Convite não pode ser excluído; preserve seu histórico.")

    def __str__(self):
        return f"Convite {self.email} — {self.contract}"


class ContractSharingEvent(models.Model):
    class EventType(models.TextChoices):
        ACCESS_GRANTED = "ACESSO_CONCEDIDO", "Acesso concedido"
        ACCESS_REVOKED = "ACESSO_REVOGADO", "Acesso revogado"
        INVITATION_CREATED = "CONVITE_CRIADO", "Convite criado"
        INVITATION_ACCEPTED = "CONVITE_ACEITO", "Convite aceito"
        INVITATION_CANCELED = "CONVITE_CANCELADO", "Convite cancelado"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="sharing_events",
        verbose_name="contrato",
    )
    access = models.ForeignKey(
        ContractAccess, on_delete=models.PROTECT, null=True, blank=True,
        related_name="events", verbose_name="acesso",
    )
    invitation = models.ForeignKey(
        ContractInvitation, on_delete=models.PROTECT, null=True, blank=True,
        related_name="events", verbose_name="convite",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="contract_sharing_events_performed", verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de compartilhamento"
        verbose_name_plural = "eventos de compartilhamento"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.contract}"


class FiscalSubstitutionStatus(models.TextChoices):
    PENDING_ACCOUNT = "PENDENTE_CONTA", "Aguardando conta aprovada"
    LINKED = "VINCULADO", "Vinculado"
    REVOKED = "REVOGADO", "Revogado"


class FiscalSubstitution(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="fiscal_substitutions",
        verbose_name="contrato",
    )
    substitute = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fiscal_substitutions",
        verbose_name="Fiscal substituto",
    )
    email = models.EmailField("e-mail do substituto", max_length=254, db_index=True)
    starts_on = models.DateField("início da substituição", db_index=True)
    ends_on = models.DateField("fim da substituição", db_index=True)
    status = models.CharField(
        "status",
        max_length=20,
        choices=FiscalSubstitutionStatus.choices,
        default=FiscalSubstitutionStatus.PENDING_ACCOUNT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fiscal_substitutions_created",
        verbose_name="criado por",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    linked_at = models.DateTimeField("vinculado em", null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="fiscal_substitutions_revoked",
        verbose_name="revogado por",
    )
    revoked_at = models.DateTimeField("revogado em", null=True, blank=True)

    class Meta:
        ordering = ("-starts_on", "-created_at", "pk")
        verbose_name = "substituição de Fiscal"
        verbose_name_plural = "substituições de Fiscal"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F("starts_on")),
                name="contracts_substitution_period_order",
            ),
        ]

    @property
    def is_effective(self):
        today = timezone.localdate()
        return (
            self.status == FiscalSubstitutionStatus.LINKED
            and self.substitute_id is not None
            and self.substitute.is_active
            and self.substitute.profile == UserProfile.FISCAL
            and self.starts_on <= today <= self.ends_on
        )

    def clean(self):
        super().clean()
        self.email = (self.email or "").strip().casefold()
        errors = {}
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            errors["ends_on"] = "O fim da substituição não pode anteceder o início."
        if self.contract_id and self.email == self.contract.responsible_fiscal.email.casefold():
            errors["email"] = "O Fiscal titular não pode substituir a si próprio."
        if self.substitute_id:
            if self.substitute.profile != UserProfile.FISCAL:
                errors["substitute"] = "O substituto deve possuir perfil Fiscal."
            if self.substitute.email.casefold() != self.email:
                errors["email"] = "O e-mail deve corresponder à conta substituta."
        if self.status == FiscalSubstitutionStatus.PENDING_ACCOUNT:
            if self.substitute_id or self.linked_at or self.revoked_by_id or self.revoked_at:
                errors["status"] = "Substituição pendente não pode conter vínculo ou revogação."
        elif self.status == FiscalSubstitutionStatus.LINKED:
            if not self.substitute_id or not self.linked_at:
                errors["status"] = "Substituição vinculada exige Fiscal e data de vínculo."
            if self.revoked_by_id or self.revoked_at:
                errors["status"] = "Substituição vinculada não pode conter revogação."
        elif not self.revoked_by_id or not self.revoked_at:
            errors["status"] = "Substituição revogada exige autor e data da revogação."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().casefold()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            "Substituição de Fiscal não pode ser excluída; use revogação auditada."
        )

    def __str__(self):
        return f"Substituição {self.email} — {self.contract}"


class FiscalSubstitutionEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "SUBSTITUICAO_CRIADA", "Substituição criada"
        LINKED = "SUBSTITUICAO_VINCULADA", "Substituição vinculada"
        REVOKED = "SUBSTITUICAO_REVOGADA", "Substituição revogada"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    substitution = models.ForeignKey(
        FiscalSubstitution,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="substituição",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="fiscal_substitution_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="fiscal_substitution_events_performed",
        verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de substituição de Fiscal"
        verbose_name_plural = "eventos de substituição de Fiscal"

    def delete(self, *args, **kwargs):
        raise ValidationError("Evento de substituição não pode ser excluído.")

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.contract}"


class ContractEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "CONTRATO_CRIADO", "Contrato criado"
        UPDATED = "CONTRATO_ATUALIZADO", "Contrato atualizado"
        STATUS_CHANGED = "STATUS_ALTERADO", "Status alterado"
        CLOSED = "CONTRATO_ENCERRADO", "Contrato encerrado"
        RESPONSIBLE_TRANSFERRED = "FISCAL_TRANSFERIDO", "Fiscal responsável transferido"
        ARCHIVED = "CONTRATO_ARQUIVADO", "Contrato arquivado logicamente"
        RESTORED = "CONTRATO_RESTAURADO", "Contrato restaurado"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="contract_events_performed",
        verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de contrato"
        verbose_name_plural = "eventos de contratos"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.contract.number}"


class CsvExportEvent(models.Model):
    class EventType(models.TextChoices):
        GENERATED = "CSV_GERADO", "CSV gerado"

    event_type = models.CharField(
        "evento", max_length=20, choices=EventType.choices,
        default=EventType.GENERATED,
    )
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="csv_export_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="csv_export_events_performed", verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de exportação CSV"
        verbose_name_plural = "eventos de exportação CSV"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.contract.number}"


class ContractItemUnit(models.TextChoices):
    HOUR = "HORA", "Hora"
    UNIT = "UNIDADE", "Unidade"
    MONTH = "MES", "Mês"
    SERVICE = "SERVICO", "Serviço"
    LICENSE = "LICENCA", "Licença"
    USER = "USUARIO", "Usuário"
    CLASS = "TURMA", "Turma"
    PACKAGE = "PACOTE", "Pacote"
    OTHER = "OUTRO", "Outro"
    CUSTOM = "PERSONALIZADA", "Personalizada"


class ContractItem(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="items",
        verbose_name="contrato",
    )
    number = models.CharField("número", max_length=100)
    external_code = models.CharField("código oficial", max_length=30, blank=True)
    description = models.TextField("descrição")
    category = models.CharField("categoria", max_length=100)
    unit = models.CharField("unidade", max_length=20, choices=ContractItemUnit.choices)
    custom_unit_name = models.CharField(
        "nome da unidade personalizada",
        max_length=50,
        blank=True,
    )
    contracted_quantity = models.DecimalField(
        "quantidade contratada",
        max_digits=20,
        decimal_places=4,
    )
    annual_reference_quantity = models.DecimalField(
        "quantidade de referência por ano contratual",
        max_digits=24,
        decimal_places=7,
        null=True,
        blank=True,
        help_text="Referência documental; não altera o valor total do item.",
    )
    annual_operational_limit = models.DecimalField(
        "limite operacional por ano contratual",
        max_digits=20,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Quantidade máxima de OS em cada ano da vigência.",
    )
    annual_reference_unit = models.CharField(
        "unidade da referência anual",
        max_length=120,
        blank=True,
    )
    unit_value = models.DecimalField(
        "valor unitário",
        max_digits=20,
        decimal_places=2,
    )
    calculation_rule = models.TextField("regra de cálculo", blank=True)
    source_reference = models.TextField("fonte de referência", blank=True)
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_contract_items",
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("contract", "number", "pk")
        verbose_name = "item contratual"
        verbose_name_plural = "itens contratuais"
        constraints = [
            models.UniqueConstraint(
                Lower("number"),
                models.F("contract"),
                name="contracts_item_number_contract_ci_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(contracted_quantity__gt=Decimal("0")),
                name="contracts_item_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_value__gte=Decimal("0.00")),
                name="contracts_item_unit_value_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(annual_reference_quantity__isnull=True)
                    | models.Q(annual_reference_quantity__gt=Decimal("0"))
                ),
                name="contracts_item_annual_reference_positive",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(annual_operational_limit__isnull=True)
                    | models.Q(annual_operational_limit__gt=Decimal("0"))
                ),
                name="contracts_item_annual_limit_positive",
            ),
        ]

    @property
    def total_value(self):
        from .calculations import calculate_item_total

        return calculate_item_total(self.contracted_quantity, self.unit_value)

    @property
    def unit_display(self):
        if self.unit == ContractItemUnit.CUSTOM:
            return self.custom_unit_name
        return self.get_unit_display()

    def clean(self):
        super().clean()
        self.number = normalized_text(self.number)
        self.external_code = normalized_text(self.external_code)
        self.description = normalized_text(self.description)
        self.category = normalized_text(self.category)
        self.custom_unit_name = normalized_text(self.custom_unit_name)
        self.annual_reference_unit = normalized_text(self.annual_reference_unit)
        self.calculation_rule = " ".join((self.calculation_rule or "").split())
        self.source_reference = " ".join((self.source_reference or "").split())
        errors = {}
        if not self.number:
            errors["number"] = "Informe o número do item."
        if not self.description:
            errors["description"] = "Informe a descrição do item."
        if not self.category:
            errors["category"] = "Informe a categoria do item."
        if self.unit == ContractItemUnit.CUSTOM and not self.custom_unit_name:
            errors["custom_unit_name"] = "Informe o nome da unidade personalizada."
        if self.unit != ContractItemUnit.CUSTOM:
            self.custom_unit_name = ""
        if self.contracted_quantity is not None and self.contracted_quantity <= Decimal("0"):
            errors["contracted_quantity"] = "A quantidade contratada deve ser maior que zero."
        if self.unit_value is not None and self.unit_value < Decimal("0.00"):
            errors["unit_value"] = "O valor unitário não pode ser negativo."
        if (
            self.annual_reference_quantity is not None
            and self.annual_reference_quantity <= Decimal("0")
        ):
            errors["annual_reference_quantity"] = (
                "A quantidade de referência anual deve ser maior que zero."
            )
        if (
            self.annual_operational_limit is not None
            and self.annual_operational_limit <= Decimal("0")
        ):
            errors["annual_operational_limit"] = (
                "O limite operacional anual deve ser maior que zero."
            )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Item {self.number} — Contrato {self.contract.number}"


class ContractItemEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "ITEM_CRIADO", "Item criado"
        UPDATED = "ITEM_ATUALIZADO", "Item atualizado"
        ACTIVATED = "ITEM_ATIVADO", "Item ativado"
        DEACTIVATED = "ITEM_INATIVADO", "Item inativado"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    item = models.ForeignKey(
        ContractItem,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="item",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="item_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="contract_item_events_performed",
        verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de item contratual"
        verbose_name_plural = "eventos de itens contratuais"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.item}"


class BudgetCommitment(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="commitments",
        verbose_name="contrato",
    )
    number = models.CharField("número", max_length=100, db_index=True)
    ped = models.CharField("PED", max_length=100, db_index=True)
    commitment_date = models.DateField("data")
    initial_value = models.DecimalField(
        "valor inicial",
        max_digits=20,
        decimal_places=2,
    )
    source = models.CharField("fonte", max_length=200)
    notes = models.TextField("observação", blank=True)
    is_active = models.BooleanField("ativo", default=True)
    closed_for_new_allocations_at = models.DateField(
        "encerrado para novos rateios em",
        null=True,
        blank=True,
        help_text="Preenchido automaticamente após o estorno do saldo do exercício.",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_budget_commitments",
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("contract", "commitment_date", "number", "pk")
        verbose_name = "empenho"
        verbose_name_plural = "empenhos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(initial_value__gte=Decimal("0.00")),
                name="contracts_commitment_initial_nonnegative",
            ),
        ]

    def movement_totals(self, *, exclude_movement_id=None):
        queryset = self.movements.all()
        if exclude_movement_id:
            queryset = queryset.exclude(pk=exclude_movement_id)
        totals = queryset.aggregate(
            reinforcements=models.Sum(
                "amount",
                filter=models.Q(movement_type=CommitmentMovement.Type.REINFORCEMENT),
                default=Decimal("0.00"),
            ),
            cancellations=models.Sum(
                "amount",
                filter=models.Q(
                    movement_type__in=(
                        CommitmentMovement.Type.CANCELLATION,
                        CommitmentMovement.Type.REVERSAL,
                    )
                ),
                default=Decimal("0.00"),
            ),
        )
        return totals["reinforcements"], totals["cancellations"]

    def movement_breakdown(self):
        totals = self.movements.aggregate(
            reinforcements=models.Sum(
                "amount",
                filter=models.Q(movement_type=CommitmentMovement.Type.REINFORCEMENT),
                default=Decimal("0.00"),
            ),
            cancellations=models.Sum(
                "amount",
                filter=models.Q(movement_type=CommitmentMovement.Type.CANCELLATION),
                default=Decimal("0.00"),
            ),
            reversals=models.Sum(
                "amount",
                filter=models.Q(movement_type=CommitmentMovement.Type.REVERSAL),
                default=Decimal("0.00"),
            ),
        )
        return totals

    @property
    def fiscal_year(self):
        return self.commitment_date.year

    @property
    def accepts_new_allocations(self):
        return self.is_active and self.closed_for_new_allocations_at is None

    @property
    def current_value(self):
        from .calculations import calculate_commitment_current_value

        reinforcements, cancellations = self.movement_totals()
        return calculate_commitment_current_value(
            self.initial_value,
            reinforcements,
            cancellations,
        )

    def clean(self):
        super().clean()
        self.number = normalized_text(self.number)
        self.ped = normalized_text(self.ped)
        self.source = normalized_text(self.source)
        self.notes = (self.notes or "").strip()
        errors = {}
        if not self.number:
            errors["number"] = "Informe o número do empenho."
        if not self.ped:
            errors["ped"] = "Informe o PED."
        if not self.source:
            errors["source"] = "Informe a fonte."
        if self.initial_value is not None and self.initial_value < Decimal("0.00"):
            errors["initial_value"] = "O valor inicial não pode ser negativo."
        if self.pk and self.initial_value is not None:
            reinforcements, cancellations = self.movement_totals()
            if self.initial_value + reinforcements - cancellations < Decimal("0.00"):
                errors["initial_value"] = (
                    "O valor inicial informado tornaria o valor atual negativo."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Empenho {self.number} — Contrato {self.contract.number}"


class CommitmentMovement(models.Model):
    class Type(models.TextChoices):
        REINFORCEMENT = "REFORCO", "Reforço"
        CANCELLATION = "ANULACAO", "Anulação"
        REVERSAL = "ESTORNO", "Estorno do saldo do exercício"

    commitment = models.ForeignKey(
        BudgetCommitment,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="empenho",
    )
    movement_type = models.CharField("tipo", max_length=10, choices=Type.choices)
    movement_date = models.DateField("data")
    amount = models.DecimalField("valor", max_digits=20, decimal_places=2)
    document_reference = models.CharField(
        "referência do documento oficial",
        max_length=255,
        blank=True,
        help_text="Obrigatória para estorno do saldo do exercício.",
    )
    notes = models.TextField("observação", blank=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_commitment_movements",
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("movement_date", "created_at", "pk")
        verbose_name = "movimentação de empenho"
        verbose_name_plural = "movimentações de empenhos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="contracts_commitment_movement_positive",
            ),
        ]

    def clean(self):
        super().clean()
        self.document_reference = normalized_text(self.document_reference)
        self.notes = (self.notes or "").strip()
        errors = {}
        if self.amount is not None and self.amount <= Decimal("0.00"):
            errors["amount"] = "O valor da movimentação deve ser maior que zero."
        if self.commitment_id and not self.commitment.is_active:
            errors["commitment"] = "Não é permitido movimentar empenho inativo."
        if self.commitment_id and self.commitment.closed_for_new_allocations_at:
            errors["commitment"] = (
                "O empenho encerrado por estorno não admite nova movimentação."
            )
        if self.movement_type == self.Type.REVERSAL and not self.document_reference:
            errors["document_reference"] = (
                "Informe a referência do documento oficial do estorno."
            )
        if (
            self.commitment_id
            and self.amount is not None
            and self.movement_type in {self.Type.CANCELLATION, self.Type.REVERSAL}
        ):
            reinforcements, cancellations = self.commitment.movement_totals(
                exclude_movement_id=self.pk
            )
            remaining = (
                self.commitment.initial_value
                + reinforcements
                - cancellations
                - self.amount
            )
            if remaining < Decimal("0.00"):
                errors["amount"] = (
                    "A anulação ou o estorno não pode tornar o valor atual negativo."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_movement_type_display()} — {self.commitment.number}"


class WorkOrderStatus(models.TextChoices):
    DRAFT = "RASCUNHO", "Rascunho"
    OPEN = "ABERTA", "Aberta"
    SIGNED = "ASSINADA", "Assinada"
    IN_PROGRESS = "EM_EXECUCAO", "Em execução"
    COMPLETED = "CONCLUIDA", "Concluída"
    HISTORICAL_IMPORTED = "HISTORICO_IMPORTADO", "Histórico importado"
    CANCELED = "CANCELADA", "Cancelada"
    SUSPENDED = "SUSPENSA", "Suspensa"


class WorkOrder(models.Model):
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="work_orders", verbose_name="contrato"
    )
    item = models.ForeignKey(
        ContractItem, on_delete=models.PROTECT, related_name="work_orders", verbose_name="item"
    )
    number = models.CharField("número", max_length=100, db_index=True)
    description = models.TextField("descrição")
    quantity = models.DecimalField(
        "quantidade", max_digits=20, decimal_places=4, null=True, blank=True
    )
    hours = models.DecimalField(
        "horas", max_digits=20, decimal_places=4, null=True, blank=True
    )
    unit_value = models.DecimalField(
        "valor unitário de referência", max_digits=20, decimal_places=2, editable=False
    )
    unit_name = models.CharField(
        "unidade de referência", max_length=50, editable=False
    )
    responsible = models.CharField("responsável", max_length=200)
    opening_date = models.DateField("data de abertura")
    signature_date = models.DateField("data de assinatura", null=True, blank=True)
    start_date = models.DateField("início", null=True, blank=True)
    deadline = models.DateField("prazo", null=True, blank=True)
    completion_date = models.DateField("conclusão", null=True, blank=True)
    status = models.CharField(
        "status",
        max_length=20,
        choices=WorkOrderStatus.choices,
        default=WorkOrderStatus.DRAFT,
        db_index=True,
    )
    process_number = models.CharField("processo", max_length=100, db_index=True)
    monthly_follow_up = models.BooleanField(
        "exige acompanhamento mensal",
        default=False,
        help_text=(
            "Marque somente quando a fonte oficial exigir atualização, "
            "medição ou faturamento mensal desta OS."
        ),
    )
    notes = models.TextField("observação", blank=True)
    cancellation_reason = models.TextField("motivo do cancelamento", blank=True)
    canceled_at = models.DateTimeField("cancelada em", null=True, blank=True)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="canceled_work_orders",
        verbose_name="cancelada por",
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_work_orders",
        verbose_name="criada por",
    )

    class Meta:
        ordering = ("contract", "opening_date", "number", "pk")
        verbose_name = "ordem de serviço"
        verbose_name_plural = "ordens de serviço"
        constraints = [
            models.CheckConstraint(
                condition=(
                    (models.Q(quantity__gt=Decimal("0")) & models.Q(hours__isnull=True))
                    | (models.Q(hours__gt=Decimal("0")) & models.Q(quantity__isnull=True))
                ),
                name="contracts_work_order_one_positive_measure",
            ),
            models.CheckConstraint(
                condition=models.Q(unit_value__gte=Decimal("0.00")),
                name="contracts_work_order_unit_value_nonnegative",
            ),
        ]

    @property
    def measure(self):
        return self.hours if self.hours is not None else self.quantity

    @property
    def total_value(self):
        from .calculations import calculate_item_total

        return calculate_item_total(self.measure, self.unit_value)

    @property
    def current_item_value_difference(self):
        return self.unit_value - self.item.unit_value

    @property
    def annual_period_context(self):
        from .periods import annual_context

        return annual_context(self.contract, self.opening_date)

    @property
    def financial_effect(self):
        if self.status in {
            WorkOrderStatus.SIGNED,
            WorkOrderStatus.IN_PROGRESS,
            WorkOrderStatus.COMPLETED,
        }:
            return True
        if self.status in {WorkOrderStatus.DRAFT, WorkOrderStatus.CANCELED}:
            return False
        return None

    def clean(self):
        super().clean()
        self.number = normalized_text(self.number)
        self.description = normalized_text(self.description)
        self.responsible = normalized_text(self.responsible)
        self.process_number = normalized_text(self.process_number)
        self.notes = (self.notes or "").strip()
        self.cancellation_reason = (self.cancellation_reason or "").strip()
        errors = {}
        required = {
            "number": (self.number, "Informe o número da OS."),
            "description": (self.description, "Informe a descrição da OS."),
            "responsible": (self.responsible, "Informe o responsável pela OS."),
            "process_number": (self.process_number, "Informe o processo da OS."),
        }
        errors.update(
            {field: message for field, (value, message) in required.items() if not value}
        )
        if self.item_id and self.contract_id and self.item.contract_id != self.contract_id:
            errors["item"] = "O item deve pertencer ao mesmo contrato da OS."
        if self.item_id:
            if not self.pk and not self.item.is_active:
                errors["item"] = "A OS exige item contratual ativo."
            uses_hours = (
                self.hours is not None
                if self.pk
                else self.item.unit == ContractItemUnit.HOUR
            )
            if uses_hours:
                if self.hours is None or self.hours <= Decimal("0"):
                    errors["hours"] = "Informe horas maiores que zero para item por hora."
                if self.quantity is not None:
                    errors["quantity"] = "Item por hora não utiliza o campo quantidade."
            else:
                if self.quantity is None or self.quantity <= Decimal("0"):
                    errors["quantity"] = "Informe quantidade maior que zero."
                if self.hours is not None:
                    errors["hours"] = "Somente item por hora utiliza o campo horas."
            if self.unit_value is not None:
                if not self.pk and self.unit_value != self.item.unit_value:
                    errors["unit_value"] = "O valor unitário deve ser o valor vigente do item."
                if self.pk:
                    original = type(self).objects.filter(pk=self.pk).values(
                        "unit_value", "unit_name"
                    ).first()
                    if original and self.unit_value != original["unit_value"]:
                        errors["unit_value"] = (
                            "O valor unitário de referência da OS não pode ser alterado."
                        )
                    if original and self.unit_name != original["unit_name"]:
                        errors["unit_name"] = (
                            "A unidade de referência da OS não pode ser alterada."
                        )
            if not self.pk and self.unit_name != self.item.unit_display:
                errors["unit_name"] = "A unidade deve ser a unidade vigente do item."
        if self.status == WorkOrderStatus.CANCELED and not self.cancellation_reason:
            errors["cancellation_reason"] = "Informe o motivo do cancelamento."
        if self.status != WorkOrderStatus.CANCELED and (
            self.cancellation_reason or self.canceled_at or self.canceled_by_id
        ):
            errors["status"] = "Dados de cancelamento exigem status Cancelada."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"OS {self.number} — Contrato {self.contract.number}"


class WorkOrderEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "OS_CRIADA", "OS criada"
        UPDATED = "OS_ATUALIZADA", "OS atualizada"
        STATUS_CHANGED = "STATUS_ALTERADO", "Status alterado"
        CANCELED = "OS_CANCELADA", "OS cancelada"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="ordem de serviço",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="work_order_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="work_order_events_performed",
        verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de ordem de serviço"
        verbose_name_plural = "eventos de ordens de serviço"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.work_order.number}"


class WorkOrderAllocationStatus(models.TextChoices):
    ACTIVE = "ATIVO", "Ativo"
    INACTIVE = "INATIVO", "Inativo"
    CANCELED = "CANCELADO", "Cancelado"


class WorkOrderAllocation(models.Model):
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name="allocations",
        verbose_name="ordem de serviço",
    )
    commitment = models.ForeignKey(
        BudgetCommitment,
        on_delete=models.PROTECT,
        related_name="allocations",
        verbose_name="empenho",
    )
    amount = models.DecimalField("valor rateado", max_digits=20, decimal_places=2)
    allocation_date = models.DateField("data")
    status = models.CharField(
        "status",
        max_length=20,
        choices=WorkOrderAllocationStatus.choices,
        default=WorkOrderAllocationStatus.ACTIVE,
        db_index=True,
    )
    cancellation_reason = models.TextField("motivo do cancelamento", blank=True)
    canceled_at = models.DateTimeField("cancelado em", null=True, blank=True)
    canceled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="canceled_work_order_allocations",
        verbose_name="cancelado por",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_work_order_allocations",
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("allocation_date", "created_at", "pk")
        verbose_name = "rateio de empenho"
        verbose_name_plural = "rateios de empenhos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="contracts_allocation_amount_positive",
            ),
        ]

    def clean(self):
        super().clean()
        self.cancellation_reason = (self.cancellation_reason or "").strip()
        errors = {}
        if self.amount is not None and self.amount <= Decimal("0.00"):
            errors["amount"] = "O valor do rateio deve ser maior que zero."
        if (
            self.work_order_id
            and self.commitment_id
            and self.work_order.contract_id != self.commitment.contract_id
        ):
            errors["commitment"] = "A OS e o empenho devem pertencer ao mesmo contrato."
        if self.status == WorkOrderAllocationStatus.CANCELED:
            if not self.cancellation_reason:
                errors["cancellation_reason"] = "Informe o motivo do cancelamento."
        elif self.cancellation_reason or self.canceled_at or self.canceled_by_id:
            errors["status"] = "Dados de cancelamento exigem status Cancelado."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Rateio da OS {self.work_order.number} no empenho {self.commitment.number}"


class WorkOrderAllocationEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "RATEIO_CRIADO", "Rateio criado"
        UPDATED = "RATEIO_ATUALIZADO", "Rateio atualizado"
        ACTIVATED = "RATEIO_ATIVADO", "Rateio ativado"
        DEACTIVATED = "RATEIO_INATIVADO", "Rateio inativado"
        CANCELED = "RATEIO_CANCELADO", "Rateio cancelado"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    allocation = models.ForeignKey(
        WorkOrderAllocation,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="rateio",
    )
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.PROTECT,
        related_name="allocation_events",
        verbose_name="ordem de serviço",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="allocation_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="work_order_allocation_events_performed",
        verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de rateio"
        verbose_name_plural = "eventos de rateios"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.allocation}"


class WorkOrderExecution(models.Model):
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT, related_name="executions",
        verbose_name="ordem de serviço",
    )
    executed_quantity = models.DecimalField(
        "quantidade executada", max_digits=20, decimal_places=4
    )
    executed_value = models.DecimalField(
        "valor executado", max_digits=20, decimal_places=2
    )
    execution_date = models.DateField("data da execução")
    competence = models.CharField(
        "competência", max_length=7, blank=True,
        help_text="Use MM/AAAA quando aplicável.",
    )
    notes = models.TextField("observação", blank=True)
    evidence_reference = models.TextField(
        "referência da evidência", blank=True,
        help_text="Identifique a evidência; o arquivo será tratado pelo módulo de documentos.",
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_work_order_executions", verbose_name="criada por",
    )

    class Meta:
        ordering = ("execution_date", "created_at", "pk")
        verbose_name = "registro de execução"
        verbose_name_plural = "registros de execução"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(executed_quantity__gt=Decimal("0")),
                name="contracts_execution_quantity_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(executed_value__gt=Decimal("0.00")),
                name="contracts_execution_value_positive",
            ),
        ]

    def clean(self):
        super().clean()
        self.competence = (self.competence or "").strip()
        self.notes = (self.notes or "").strip()
        self.evidence_reference = (self.evidence_reference or "").strip()
        errors = {}
        if self.executed_quantity is not None and self.executed_quantity <= Decimal("0"):
            errors["executed_quantity"] = "A quantidade executada deve ser maior que zero."
        if self.executed_value is not None and self.executed_value <= Decimal("0.00"):
            errors["executed_value"] = "O valor executado deve ser maior que zero."
        if self.competence:
            parts = self.competence.split("/")
            if (
                len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 4
                or not all(part.isdigit() for part in parts)
                or not 1 <= int(parts[0]) <= 12
            ):
                errors["competence"] = "Informe a competência no formato MM/AAAA."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Execução da OS {self.work_order.number} em {self.execution_date:%d/%m/%Y}"


class WorkOrderExecutionEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "EXECUCAO_CRIADA", "Execução criada"
        UPDATED = "EXECUCAO_ATUALIZADA", "Execução atualizada"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    execution = models.ForeignKey(
        WorkOrderExecution, on_delete=models.PROTECT, related_name="events",
        verbose_name="execução",
    )
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT, related_name="execution_events",
        verbose_name="ordem de serviço",
    )
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="execution_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="work_order_execution_events_performed", verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de execução"
        verbose_name_plural = "eventos de execução"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.execution}"


class Invoice(models.Model):
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="invoices",
        verbose_name="contrato",
    )
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT, related_name="invoices",
        verbose_name="ordem de serviço",
    )
    item = models.ForeignKey(
        ContractItem, on_delete=models.PROTECT, related_name="invoices",
        null=True, blank=True, verbose_name="item",
    )
    allocation = models.ForeignKey(
        WorkOrderAllocation, on_delete=models.PROTECT, related_name="invoices",
        null=True, blank=True, verbose_name="rateio",
    )
    number = models.CharField("número", max_length=100, db_index=True)
    series = models.CharField("série", max_length=50, db_index=True)
    supplier_name = models.CharField("fornecedor", max_length=200)
    supplier_tax_id = models.CharField(
        "CNPJ/CPF", max_length=14, validators=[tax_id_validator], db_index=True
    )
    issue_date = models.DateField("data de emissão")
    competence = models.CharField("competência", max_length=7)
    gross_value = models.DecimalField("valor bruto", max_digits=20, decimal_places=2)
    deduction_value = models.DecimalField(
        "glosa", max_digits=20, decimal_places=2, default=Decimal("0.00")
    )
    accepted_value = models.DecimalField(
        "valor aceito", max_digits=20, decimal_places=2
    )
    process_number = models.CharField("processo", max_length=100, blank=True, db_index=True)
    status = models.CharField("status informado", max_length=50, db_index=True)
    document_reference = models.TextField(
        "referência do documento", blank=True,
        help_text="Identifique o documento; o arquivo será tratado pelo módulo de documentos.",
    )
    document_hash = models.CharField(
        "hash SHA-256", max_length=64, blank=True, db_index=True,
        help_text="Opcional nesta etapa; informe 64 caracteres hexadecimais quando disponível.",
    )
    notes = models.TextField("observação", blank=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_invoices", verbose_name="criada por",
    )

    class Meta:
        ordering = ("issue_date", "number", "series", "pk")
        verbose_name = "nota fiscal"
        verbose_name_plural = "notas fiscais"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(gross_value__gt=Decimal("0.00")),
                name="contracts_invoice_gross_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(deduction_value__gte=Decimal("0.00")),
                name="contracts_invoice_deduction_nonnegative",
            ),
            models.CheckConstraint(
                condition=models.Q(accepted_value__gte=Decimal("0.00")),
                name="contracts_invoice_accepted_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        self.number = normalized_text(self.number)
        self.series = normalized_text(self.series)
        self.supplier_name = normalized_text(self.supplier_name)
        self.supplier_tax_id = "".join(filter(str.isdigit, self.supplier_tax_id or ""))
        self.competence = (self.competence or "").strip()
        self.process_number = normalized_text(self.process_number)
        self.status = normalized_text(self.status)
        self.document_reference = (self.document_reference or "").strip()
        self.document_hash = (self.document_hash or "").strip().lower()
        self.notes = (self.notes or "").strip()
        errors = {}
        for field, value, message in (
            ("number", self.number, "Informe o número da Nota Fiscal."),
            ("series", self.series, "Informe a série da Nota Fiscal."),
            ("supplier_name", self.supplier_name, "Informe o fornecedor."),
            ("status", self.status, "Informe o status constante na fonte."),
        ):
            if not value:
                errors[field] = message
        parts = self.competence.split("/")
        if (
            len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 4
            or not all(part.isdigit() for part in parts)
            or not 1 <= int(parts[0]) <= 12
        ):
            errors["competence"] = "Informe a competência no formato MM/AAAA."
        if self.gross_value is not None and self.gross_value <= Decimal("0.00"):
            errors["gross_value"] = "O valor bruto deve ser maior que zero."
        if self.deduction_value is not None and self.deduction_value < Decimal("0.00"):
            errors["deduction_value"] = "A glosa não pode ser negativa."
        if self.accepted_value is not None and self.accepted_value < Decimal("0.00"):
            errors["accepted_value"] = "O valor aceito não pode ser negativo."
        if (
            self.gross_value is not None and self.deduction_value is not None
            and self.deduction_value > self.gross_value
        ):
            errors["deduction_value"] = "A glosa não pode superar o valor bruto."
        if (
            self.gross_value is not None and self.accepted_value is not None
            and self.accepted_value > self.gross_value
        ):
            errors["accepted_value"] = "O valor aceito não pode superar o valor bruto."
        if self.work_order_id and self.contract_id and self.work_order.contract_id != self.contract_id:
            errors["work_order"] = "A OS deve pertencer ao mesmo contrato da Nota Fiscal."
        if self.item_id:
            if self.item.contract_id != self.contract_id:
                errors["item"] = "O item deve pertencer ao mesmo contrato da Nota Fiscal."
            elif self.work_order_id and self.item_id != self.work_order.item_id:
                errors["item"] = "O item informado deve corresponder ao item da OS."
        if self.allocation_id:
            if self.allocation.work_order_id != self.work_order_id:
                errors["allocation"] = "O rateio deve pertencer à mesma OS da Nota Fiscal."
            elif self.allocation.work_order.contract_id != self.contract_id:
                errors["allocation"] = "O rateio deve pertencer ao mesmo contrato da Nota Fiscal."
        if self.contract_id:
            if self.supplier_name.casefold() != self.contract.supplier_name.casefold():
                errors["supplier_name"] = "O fornecedor deve corresponder ao contrato."
            if self.supplier_tax_id != self.contract.supplier_tax_id:
                errors["supplier_tax_id"] = "O CNPJ/CPF deve corresponder ao contrato."
        if self.document_hash and (
            len(self.document_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.document_hash)
        ):
            errors["document_hash"] = "Informe um hash SHA-256 hexadecimal com 64 caracteres."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"NF {self.number}/{self.series} — OS {self.work_order.number}"


class InvoiceEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "NF_CRIADA", "Nota Fiscal criada"
        UPDATED = "NF_ATUALIZADA", "Nota Fiscal atualizada"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="events", verbose_name="nota fiscal"
    )
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.PROTECT, related_name="invoice_events",
        verbose_name="ordem de serviço",
    )
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="invoice_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="invoice_events_performed", verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de Nota Fiscal"
        verbose_name_plural = "eventos de Notas Fiscais"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.invoice}"


class Payment(models.Model):
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="payments",
        verbose_name="nota fiscal",
    )
    amount = models.DecimalField("valor pago", max_digits=20, decimal_places=2)
    payment_date = models.DateField("data do pagamento")
    competence = models.CharField("competência", max_length=7, blank=True)
    status = models.CharField("status informado", max_length=50, db_index=True)
    process_number = models.CharField(
        "processo", max_length=100, blank=True, db_index=True
    )
    attestation_reference = models.TextField("referência do Atesto")
    raer_reference = models.TextField("referência da RAER")
    homologation_reference = models.TextField("referência do Termo de Homologação")
    evidence_reference = models.TextField(
        "referência do comprovante", blank=True,
        help_text="Identifique o comprovante; o arquivo será tratado pelo módulo de documentos.",
    )
    notes = models.TextField("observação", blank=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="created_payments", verbose_name="criado por",
    )

    class Meta:
        ordering = ("payment_date", "pk")
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=Decimal("0.00")),
                name="contracts_payment_amount_positive",
            ),
        ]

    def clean(self):
        super().clean()
        self.competence = (self.competence or "").strip()
        self.status = normalized_text(self.status)
        self.process_number = normalized_text(self.process_number)
        self.attestation_reference = (self.attestation_reference or "").strip()
        self.raer_reference = (self.raer_reference or "").strip()
        self.homologation_reference = (self.homologation_reference or "").strip()
        self.evidence_reference = (self.evidence_reference or "").strip()
        self.notes = (self.notes or "").strip()
        errors = {}
        if self.amount is not None and self.amount <= Decimal("0.00"):
            errors["amount"] = "O valor pago deve ser maior que zero."
        if self.competence:
            parts = self.competence.split("/")
            if (
                len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 4
                or not all(part.isdigit() for part in parts)
                or not 1 <= int(parts[0]) <= 12
            ):
                errors["competence"] = "Informe a competência no formato MM/AAAA."
        if not self.status:
            errors["status"] = "Informe o status constante na fonte."
        for field, value, label in (
            ("attestation_reference", self.attestation_reference, "Atesto"),
            ("raer_reference", self.raer_reference, "RAER"),
            ("homologation_reference", self.homologation_reference, "Termo de Homologação"),
        ):
            if not value:
                errors[field] = f"Informe a referência do {label}."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Pagamento de R$ {self.amount} — {self.invoice}"


class PaymentEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "PAGAMENTO_CRIADO", "Pagamento criado"
        UPDATED = "PAGAMENTO_ATUALIZADO", "Pagamento atualizado"

    event_type = models.CharField("evento", max_length=40, choices=EventType.choices)
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, related_name="events", verbose_name="pagamento"
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, related_name="payment_events",
        verbose_name="nota fiscal",
    )
    contract = models.ForeignKey(
        Contract, on_delete=models.PROTECT, related_name="payment_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="payment_events_performed", verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de pagamento"
        verbose_name_plural = "eventos de pagamentos"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.payment}"


class BudgetCommitmentEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "EMPENHO_CRIADO", "Empenho criado"
        UPDATED = "EMPENHO_ATUALIZADO", "Empenho atualizado"
        ACTIVATED = "EMPENHO_ATIVADO", "Empenho ativado"
        DEACTIVATED = "EMPENHO_INATIVADO", "Empenho inativado"
        MOVEMENT_CREATED = "MOVIMENTO_CRIADO", "Movimentação criada"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    commitment = models.ForeignKey(
        BudgetCommitment,
        on_delete=models.PROTECT,
        related_name="events",
        verbose_name="empenho",
    )
    contract = models.ForeignKey(
        Contract,
        on_delete=models.PROTECT,
        related_name="commitment_events",
        verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="budget_commitment_events_performed",
        verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de empenho"
        verbose_name_plural = "eventos de empenhos"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.commitment.number}"
