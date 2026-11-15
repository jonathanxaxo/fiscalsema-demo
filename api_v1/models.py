import uuid

from django.conf import settings
from django.db import models


class ApiCredential(models.Model):
    class AccessMode(models.TextChoices):
        READ_ONLY = "READ_ONLY", "Somente leitura"
        CONTROLLED_DRAFT = "CONTROLLED_DRAFT", "Leitura e rascunhos controlados"

    name = models.CharField("nome", max_length=120)
    access_mode = models.CharField(
        "modo de acesso", max_length=30, choices=AccessMode.choices,
        default=AccessMode.READ_ONLY,
    )
    token_prefix = models.CharField("prefixo", max_length=16, unique=True, editable=False)
    token_hash = models.CharField("hash do token", max_length=64, editable=False)
    authorized_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="api_credentials", verbose_name="usuário autorizador",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="created_api_credentials", verbose_name="criada por",
    )
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    expires_at = models.DateTimeField("expira em", null=True, blank=True)
    revoked_at = models.DateTimeField("revogada em", null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="revoked_api_credentials", verbose_name="revogada por",
    )
    last_used_at = models.DateTimeField("último uso", null=True, blank=True)
    rate_window_started_at = models.DateTimeField("início da janela", null=True, blank=True)
    rate_window_count = models.PositiveIntegerField("requisições na janela", default=0)

    class Meta:
        ordering = ("name", "pk")
        verbose_name = "credencial da API"
        verbose_name_plural = "credenciais da API"

    def __str__(self):
        return f"{self.name} ({self.token_prefix})"


class ApiAccessEvent(models.Model):
    class EventType(models.TextChoices):
        QUERY = "CONSULTA", "Consulta autorizada"
        DENIED = "NEGADA", "Consulta negada"
        CONNECTION_AUTHORIZED = "CONEXAO_AUTORIZADA", "Conexão MCP autorizada ou renovada"
        CONNECTION_REVOKED = "CONEXAO_REVOGADA", "Conexão MCP revogada"

    event_type = models.CharField("evento", max_length=20, choices=EventType.choices)
    credential = models.ForeignKey(
        ApiCredential, on_delete=models.PROTECT, null=True, blank=True,
        related_name="events", verbose_name="credencial",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="api_access_events", verbose_name="usuário autorizador",
    )
    contract = models.ForeignKey(
        "contracts.Contract", on_delete=models.PROTECT, null=True, blank=True,
        related_name="api_access_events", verbose_name="contrato",
    )
    endpoint = models.CharField("endpoint", max_length=255)
    method = models.CharField("método", max_length=10)
    status_code = models.PositiveSmallIntegerField("status HTTP")
    result_count = models.PositiveIntegerField("quantidade de resultados", default=0)
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de acesso à API"
        verbose_name_plural = "eventos de acesso à API"


class AssistantDraft(models.Model):
    class Operation(models.TextChoices):
        CREATE = "CRIAR", "Criar registro"
        UPDATE = "ATUALIZAR", "Atualizar registro existente"

    class ConfidenceLevel(models.TextChoices):
        CONFIRMED = "CONFIRMADO", "Confirmado"
        FOUND_IN_SOURCE = "ENCONTRADO_EM_FONTE", "Encontrado em fonte"
        SYSTEM_CALCULATED = "CALCULADO_PELO_SISTEMA", "Calculado pelo sistema"
        INFERRED = "INFERIDO", "Inferido"
        ESTIMATED = "ESTIMADO", "Estimado"
        PENDING = "PENDENTE", "Pendente"
        DIVERGENT = "DIVERGENTE", "Divergente"

    class SourceAuthority(models.TextChoices):
        VALIDATED_SYSTEM = "SISTEMA_HOMOLOGADO", "Dado homologado no sistema"
        VALIDATED_OFFICIAL_DOCUMENT = "DOCUMENTO_OFICIAL_VALIDADO", "Documento oficial validado"
        CONFIRMED_IMPORT = "IMPORTACAO_CONFIRMADA", "Importação confirmada"
        AUTOMATED_EXTRACTION = "EXTRACAO_AUTOMATICA", "Extração automática da IA"

    class EntityType(models.TextChoices):
        CONTRACT = "CONTRATO", "Contrato"
        ITEM = "ITEM", "Item"
        COMMITMENT = "EMPENHO", "Empenho"
        WORK_ORDER = "OS", "Ordem de Serviço"
        ALLOCATION = "RATEIO", "Rateio"
        EXECUTION = "EXECUCAO", "Execução"
        INVOICE = "NF", "Nota Fiscal"
        PAYMENT = "PAGAMENTO", "Pagamento"

    class Status(models.TextChoices):
        PENDING = "PENDENTE", "Pendente de revisão"
        CONFIRMED = "CONFIRMADO", "Confirmado"
        REJECTED = "REJEITADO", "Rejeitado"

    entity_type = models.CharField("tipo", max_length=20, choices=EntityType.choices)
    operation = models.CharField(
        "operação", max_length=20, choices=Operation.choices, default=Operation.CREATE,
    )
    batch_id = models.UUIDField("lote", default=uuid.uuid4, db_index=True)
    contract = models.ForeignKey(
        "contracts.Contract", on_delete=models.PROTECT, null=True, blank=True,
        related_name="assistant_drafts", verbose_name="contrato",
    )
    context = models.JSONField("contexto", default=dict)
    payload = models.JSONField("dados propostos", default=dict)
    evidence = models.JSONField("fontes e evidências", default=list)
    source_summary = models.TextField("resumo da origem")
    source_authority = models.CharField(
        "autoridade da fonte", max_length=40, choices=SourceAuthority.choices,
        default=SourceAuthority.AUTOMATED_EXTRACTION,
    )
    confidence_level = models.CharField(
        "nível de confiança", max_length=30, choices=ConfidenceLevel.choices,
        default=ConfidenceLevel.FOUND_IN_SOURCE,
    )
    comparison = models.JSONField("comparação com o sistema", default=list, blank=True)
    consistency_result = models.JSONField(
        "resultado da consistência", default=dict, blank=True,
    )
    baseline_hash = models.CharField(
        "hash do estado comparado", max_length=64, blank=True, editable=False,
    )
    requires_human_confirmation = models.BooleanField(
        "exige confirmação humana", default=True, editable=False,
    )
    status = models.CharField(
        "status", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True,
    )
    created_by_credential = models.ForeignKey(
        ApiCredential, on_delete=models.PROTECT, related_name="drafts",
        null=True, blank=True, verbose_name="credencial técnica",
    )
    # Sprint 28: rascunho proposto por cliente MCP conectado com a identidade da pessoa.
    created_by_application = models.ForeignKey(
        settings.OAUTH2_PROVIDER_APPLICATION_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assistant_drafts",
        verbose_name="cliente MCP (OAuth)",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="assistant_drafts", verbose_name="usuário autorizador",
    )
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="reviewed_assistant_drafts", verbose_name="revisado por",
    )
    reviewed_at = models.DateTimeField("revisado em", null=True, blank=True)
    rejection_reason = models.TextField("motivo da rejeição", blank=True)
    target_model = models.CharField("modelo gravado", max_length=100, blank=True)
    target_id = models.PositiveBigIntegerField("registro gravado", null=True, blank=True)
    # Sprint 30: execução autorizada pelo MCP com código de uso único.
    expires_at = models.DateTimeField("válido até", null=True, blank=True)
    idempotency_key = models.CharField("chave de repetição", max_length=80, blank=True, default="")
    confirmation_code_hash = models.CharField(
        "hash do código de confirmação", max_length=64, blank=True, default="", editable=False,
    )
    confirmation_code_expires_at = models.DateTimeField("código válido até", null=True, blank=True)
    confirmation_code_attempts = models.PositiveSmallIntegerField("tentativas do código", default=0)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "rascunho assistido"
        verbose_name_plural = "rascunhos assistidos"
        constraints = [
            models.UniqueConstraint(
                fields=("requested_by", "idempotency_key"),
                condition=~models.Q(idempotency_key=""),
                name="rascunho_chave_repeticao_unica",
            ),
        ]


class AssistantDraftEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "RASCUNHO_CRIADO", "Rascunho criado"
        CONFIRMED = "RASCUNHO_CONFIRMADO", "Rascunho confirmado"
        REJECTED = "RASCUNHO_REJEITADO", "Rascunho rejeitado"
        VALIDATION_FAILED = "VALIDACAO_FALHOU", "Confirmação recusada pela validação"
        CODE_ISSUED = "CODIGO_EMITIDO", "Código de confirmação emitido"
        CODE_REFUSED = "CODIGO_RECUSADO", "Código de confirmação recusado"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    draft = models.ForeignKey(
        AssistantDraft, on_delete=models.PROTECT, related_name="events", verbose_name="rascunho",
    )
    contract = models.ForeignKey(
        "contracts.Contract", on_delete=models.PROTECT, null=True, blank=True,
        related_name="assistant_draft_events", verbose_name="contrato",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="assistant_draft_events", verbose_name="autor",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de rascunho assistido"
        verbose_name_plural = "eventos de rascunhos assistidos"
