"""MCP remoto por identidade (Sprint 28).

Endpoint ``/mcp`` no transporte "Streamable HTTP" do MCP, sem estado: cada
requisição é um JSON-RPC 2.0 com ``Authorization: Bearer`` emitido pelo nosso
servidor OAuth. O token pertence a uma pessoa; as ferramentas usam os mesmos
serviços de visibilidade da interface web, então a IA enxerga exatamente o
que a pessoa já pode ver.

Regras que não mudam:
- nada de SQL, banco direto ou ferramenta genérica de edição;
- ``propor_rascunho`` só cria proposta pendente (exige o escopo
  ``fiscalsema.propor``); confirmar continua sendo ação humana na web;
- homologação, atesto, liquidação e pagamento nunca são feitos pela IA;
- toda chamada de ferramenta é auditada (sem guardar o conteúdo devolvido).
"""

import json
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from accounts.models import AccountStatus
from contracts.accountability import build_accountability_snapshot
from contracts.services import (
    allocations_visible_to, commitments_visible_to, contract_financial_position,
    contracts_visible_to, executions_visible_to, invoice_check_report,
    invoices_visible_to, items_visible_to, payments_visible_to, work_orders_visible_to,
)
from documents.services import document_metadata_visible_to

from .analise import AnalysisError, analyze_divergences

from .drafts import DraftValidationError, create_assistant_draft
from .execucao import ExecutionRefused, execute_with_code
from .models import ApiAccessEvent, AssistantDraft
from .oauth import client_details
from .serializers import (
    allocation_data, commitment_data, contract_data, document_data, execution_data,
    invoice_data, item_data, payment_data, primitive, work_order_data,
)
from .views import PAYMENT_NOTICE, accountability_data, draft_data

ENDPOINT = "/mcp"
SUPPORTED_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26")
SERVER_INFO = {"name": "fiscalsema-demo", "title": "FiscalSema Demo", "version": "2.0.0"}
SCOPE_READ = "fiscalsema.ler"
SCOPE_PROPOSE = "fiscalsema.propor"
SCOPE_EXECUTE = "fiscalsema.executar"
MAX_BODY_BYTES = 200_000

INSTRUCTIONS = (
    "Servidor MCP do FiscalSema Demo (somente dados fictícios). Você age com a "
    "identidade e as permissões da pessoa que autorizou a conexão. Consultas são "
    "informativas. propor_rascunho cria apenas uma proposta pendente: a pessoa "
    "revisa no FiscalSema e confirma lá ou gera um código de confirmação. "
    "executar_proposta só funciona com esse código, digitado pela pessoa; um 'sim' "
    "no chat não basta. Nunca invente ou adivinhe códigos. Homologação, atesto, "
    "liquidação e pagamento nunca são feitos por IA. NF com is_returned=true foi "
    "devolvida para correção e não entra em nenhum cálculo; dimensioned_value é o "
    "valor dimensionado dos serviços homologados que a NF cobra."
)

PAGE_PROPS = {
    "page": {"type": "integer", "minimum": 1},
    "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
}
CONTRACT_PROPS = {"contract_id": {"type": "integer", "minimum": 1}, **PAGE_PROPS}
READ_ONLY = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}


def _contract_tool(name, title, description):
    return {
        "name": name, "title": title, "description": description,
        "inputSchema": {"type": "object", "properties": CONTRACT_PROPS,
                        "required": ["contract_id"], "additionalProperties": False},
        "annotations": READ_ONLY, "_scope": SCOPE_READ,
    }


TOOLS = [
    {
        "name": "listar_contratos_autorizados", "title": "Listar contratos autorizados",
        "description": "Lista somente os contratos que a pessoa conectada pode ver.",
        "inputSchema": {"type": "object", "properties": PAGE_PROPS, "additionalProperties": False},
        "annotations": READ_ONLY, "_scope": SCOPE_READ,
    },
    _contract_tool("consultar_resumo_contrato", "Resumo do contrato",
                   "Resumo, contagens e posição financeira de um contrato autorizado."),
    _contract_tool("consultar_itens", "Itens do contrato", "Itens de um contrato autorizado."),
    _contract_tool("consultar_empenhos", "Empenhos", "Empenhos de um contrato autorizado."),
    _contract_tool("consultar_ordens_servico", "Ordens de serviço",
                   "Ordens de serviço de um contrato autorizado."),
    _contract_tool("consultar_notas_fiscais", "Notas fiscais",
                   "Notas fiscais de um contrato autorizado."),
    _contract_tool("consultar_pendencias", "Prestação de contas e pendências",
                   "Prestação de contas, conferências de NF e pendências do contrato."),
    # Sprint 29: consultas e análise (somente leitura).
    _contract_tool("consultar_rateios", "Rateios", "Rateios das ordens de serviço do contrato."),
    _contract_tool("consultar_execucoes", "Execuções", "Execuções registradas nas ordens de serviço."),
    _contract_tool("consultar_pagamentos", "Pagamentos",
                   "Pagamentos registrados (consulta informativa, não autoriza pagamento)."),
    _contract_tool("consultar_posicao_financeira", "Posição financeira",
                   "Valor contratado, empenhado, executado, faturado e pago do contrato."),
    _contract_tool("listar_documentos", "Documentos do contrato",
                   "Lista nome, tipo, versão e data dos documentos (sem baixar o arquivo)."),
    {
        "name": "conferir_nota_fiscal", "title": "Conferir nota fiscal",
        "description": "Conferência automática de uma nota fiscal autorizada (informativa).",
        "inputSchema": {"type": "object", "properties": {"invoice_id": {"type": "integer", "minimum": 1}},
                        "required": ["invoice_id"], "additionalProperties": False},
        "annotations": READ_ONLY, "_scope": SCOPE_READ,
    },
    {
        "name": "analisar_divergencias", "title": "Analisar divergências com documento",
        "description": (
            "Compara valores lidos num documento com um registro gravado e aponta, campo a "
            "campo, IGUAL, DIFERENTE, AUSENTE_NO_DOCUMENTO ou VAZIO_NO_SISTEMA. Não grava nada."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "enum": list(AssistantDraft.EntityType.values)},
                "target_id": {"type": "integer", "minimum": 1},
                "document_values": {"type": "object", "description": "campo: valor lido no documento"},
            },
            "required": ["entity_type", "target_id", "document_values"],
            "additionalProperties": False,
        },
        "annotations": READ_ONLY, "_scope": SCOPE_READ,
    },
    {
        "name": "consultar_meus_rascunhos", "title": "Meus rascunhos propostos",
        "description": "Situação (pendente, confirmado, rejeitado) dos rascunhos da pessoa conectada.",
        "inputSchema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": list(AssistantDraft.Status.values)},
                           **PAGE_PROPS},
            "additionalProperties": False,
        },
        "annotations": READ_ONLY, "_scope": SCOPE_READ,
    },
    {
        "name": "propor_rascunho", "title": "Propor rascunho (pendente)",
        "description": (
            "Cria somente uma proposta pendente de confirmação humana na interface web. "
            "Não executa, não confirma, não rejeita e não altera registros."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "enum": list(AssistantDraft.EntityType.values)},
                "operation": {"type": "string", "enum": list(AssistantDraft.Operation.values)},
                "context": {"type": "object"},
                "payload": {"type": "object"},
                "source_summary": {"type": "string", "minLength": 1},
                "source_authority": {
                    "type": "string",
                    "enum": [value for value in AssistantDraft.SourceAuthority.values
                             if value != AssistantDraft.SourceAuthority.VALIDATED_SYSTEM],
                },
                "confidence_level": {
                    "type": "string",
                    "enum": [value for value in AssistantDraft.ConfidenceLevel.values
                             if value != AssistantDraft.ConfidenceLevel.SYSTEM_CALCULATED],
                },
                "evidence": {"type": "array", "items": {"type": "object"}, "minItems": 1},
                "idempotency_key": {
                    "type": "string", "minLength": 8, "maxLength": 80,
                    "description": "Opcional: repetir a mesma chave devolve a mesma proposta.",
                },
            },
            "required": ["entity_type", "operation", "context", "payload",
                         "source_summary", "source_authority", "confidence_level", "evidence"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": False, "openWorldHint": False},
        "_scope": SCOPE_PROPOSE,
    },
    {
        "name": "executar_proposta", "title": "Executar proposta com código",
        "description": (
            "Executa uma proposta pendente desta conexão SOMENTE com o código de confirmação "
            "que a pessoa gerou no FiscalSema e digitou no chat. Sem código, peça à pessoa "
            "para abrir a proposta no FiscalSema. Pagamentos nunca são executados."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "draft_id": {"type": "integer", "minimum": 1},
                "codigo": {"type": "string", "minLength": 8, "maxLength": 12},
            },
            "required": ["draft_id", "codigo"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": True,
                        "idempotentHint": True, "openWorldHint": False},
        "_scope": SCOPE_EXECUTE,
    },
]
TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}


class ToolError(Exception):
    """Erro de ferramenta com mensagem segura para a IA."""


def _public(tool):
    return {key: value for key, value in tool.items() if not key.startswith("_")}


def _int(arguments, key, default=None, *, minimum=1, maximum=None):
    value = arguments.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum or (
        maximum is not None and value > maximum
    ):
        raise ToolError(f"Parâmetro '{key}' inválido.")
    return value


def _page(arguments, queryset, serializer):
    page_number = _int(arguments, "page", 1)
    page_size = _int(arguments, "page_size", settings.API_DEFAULT_PAGE_SIZE,
                     maximum=settings.API_MAX_PAGE_SIZE)
    paginator = Paginator(queryset, page_size)
    if page_number > max(1, paginator.num_pages):
        raise ToolError("Página não encontrada.")
    page = paginator.get_page(page_number)
    results = [serializer(item) for item in page.object_list]
    return {"count": paginator.count, "page": page.number, "pages": paginator.num_pages,
            "results": results}, len(results)


class ToolContext:
    def __init__(self, user, application, base_url=""):
        self.user, self.application = user, application
        self.base_url = base_url
        self.contract = None

    def contract_from(self, arguments):
        contract_id = _int(arguments, "contract_id")
        contract = contracts_visible_to(self.user).filter(pk=contract_id).first()
        if contract is None:
            raise ToolError("Contrato não encontrado ou sem permissão.")
        self.contract = contract
        return contract


def run_tool(name, arguments, ctx):
    """Executa a ferramenta e devolve ``(dados, quantidade_de_resultados)``."""
    user = ctx.user
    if name == "listar_contratos_autorizados":
        return _page(arguments, contracts_visible_to(user), contract_data)
    if name == "propor_rascunho":
        return _propose(arguments, ctx)
    if name == "executar_proposta":
        return _execute(arguments, ctx)
    if name == "conferir_nota_fiscal":
        invoice = invoices_visible_to(user).filter(pk=_int(arguments, "invoice_id")).first()
        if invoice is None:
            raise ToolError("Nota fiscal não encontrada ou sem permissão.")
        ctx.contract = invoice.contract
        return {"invoice": invoice_data(invoice), "check": primitive(invoice_check_report(invoice)),
                "decision_notice": PAYMENT_NOTICE}, 1
    if name == "analisar_divergencias":
        try:
            data, ctx.contract = analyze_divergences(
                user=user, entity_type=arguments.get("entity_type"),
                target_id=_int(arguments, "target_id"),
                document_values=arguments.get("document_values"),
            )
        except AnalysisError as exc:
            raise ToolError(str(exc)) from exc
        return data, len(data["fields"])
    if name == "consultar_meus_rascunhos":
        queryset = AssistantDraft.objects.select_related("requested_by").filter(requested_by=user)
        status = arguments.get("status")
        if status is not None:
            if status not in AssistantDraft.Status.values:
                raise ToolError("Parâmetro 'status' inválido.")
            queryset = queryset.filter(status=status)
        return _page(arguments, queryset, draft_data)
    contract = ctx.contract_from(arguments)
    if name == "consultar_resumo_contrato":
        return {
            "contract": contract_data(contract),
            "counts": {
                "items": items_visible_to(user).filter(contract=contract).count(),
                "commitments": commitments_visible_to(user).filter(contract=contract).count(),
                "work_orders": work_orders_visible_to(user).filter(contract=contract).count(),
                "invoices": invoices_visible_to(user).filter(contract=contract).count(),
                "payments": payments_visible_to(user).filter(invoice__contract=contract).count(),
            },
            "financial": primitive(contract_financial_position(contract)),
            "decision_notice": PAYMENT_NOTICE,
        }, 1
    if name == "consultar_itens":
        return _page(arguments, items_visible_to(user).filter(contract=contract), item_data)
    if name == "consultar_empenhos":
        return _page(arguments, commitments_visible_to(user).filter(contract=contract), commitment_data)
    if name == "consultar_ordens_servico":
        return _page(arguments, work_orders_visible_to(user).filter(contract=contract), work_order_data)
    if name == "consultar_notas_fiscais":
        data, count = _page(arguments, invoices_visible_to(user).filter(contract=contract), invoice_data)
        data["decision_notice"] = PAYMENT_NOTICE
        return data, count
    if name == "consultar_rateios":
        return _page(arguments, allocations_visible_to(user).filter(work_order__contract=contract),
                     allocation_data)
    if name == "consultar_execucoes":
        return _page(arguments, executions_visible_to(user).filter(work_order__contract=contract),
                     execution_data)
    if name == "consultar_pagamentos":
        data, count = _page(arguments, payments_visible_to(user).filter(invoice__contract=contract),
                            payment_data)
        data["decision_notice"] = PAYMENT_NOTICE
        return data, count
    if name == "consultar_posicao_financeira":
        return {"contract_id": contract.pk, "position": primitive(contract_financial_position(contract)),
                "decision_notice": PAYMENT_NOTICE}, 1
    if name == "listar_documentos":
        return _page(
            arguments,
            document_metadata_visible_to(user).filter(contract=contract),
            _document_summary,
        )
    if name == "consultar_pendencias":
        return accountability_data(build_accountability_snapshot(contract, {})), 1
    raise ToolError("Ferramenta desconhecida.")


def _document_summary(document):
    data = document_data(document)
    data.pop("content_url", None)  # o MCP não baixa arquivos
    return data


def _draft_url(draft):
    return reverse("assistant_drafts:detail", args=[draft.pk])


def _execute(arguments, ctx):
    draft_id = _int(arguments, "draft_id")
    code = arguments.get("codigo")
    if not isinstance(code, str):
        raise ToolError("Informe o código de confirmação digitado pela pessoa.")
    try:
        draft, repeated = execute_with_code(draft_id=draft_id, code=code, actor=ctx.user,
                                            application=ctx.application)
    except ExecutionRefused as exc:
        raise ToolError(str(exc)) from exc
    ctx.contract = draft.contract
    return {
        "data": draft_data(draft),
        "result": "ja_executada_antes" if repeated else "executada",
        "message": (
            "Esta proposta já estava executada; nada foi gravado de novo." if repeated
            else f"Executada após confirmação humana por código. Registro {draft.target_model} #{draft.target_id}."
        ),
    }, 1


def _propose(arguments, ctx):
    allowed = set(TOOLS_BY_NAME["propor_rascunho"]["inputSchema"]["properties"])
    if set(arguments) - allowed:
        raise ToolError("Parâmetros não permitidos em propor_rascunho.")
    key = arguments.get("idempotency_key") or ""
    if key and (not isinstance(key, str) or not 8 <= len(key) <= 80):
        raise ToolError("Parâmetro 'idempotency_key' inválido.")
    if key:
        existing = AssistantDraft.objects.select_related("requested_by").filter(
            requested_by=ctx.user, idempotency_key=key,
        ).first()
        if existing is not None:
            ctx.contract = existing.contract
            return {"data": draft_data(existing), "repeated": True,
                    "next_action": "Proposta já existente com esta chave; nada foi criado de novo."}, 1
    try:
        draft = create_assistant_draft(
            entity_type=arguments.get("entity_type"),
            operation=arguments.get("operation", AssistantDraft.Operation.CREATE),
            context=arguments.get("context", {}), payload=arguments.get("payload", {}),
            evidence=arguments.get("evidence", []),
            source_summary=arguments.get("source_summary", ""),
            source_authority=arguments.get(
                "source_authority", AssistantDraft.SourceAuthority.AUTOMATED_EXTRACTION),
            confidence_level=arguments.get(
                "confidence_level", AssistantDraft.ConfidenceLevel.FOUND_IN_SOURCE),
            application=ctx.application, actor=ctx.user, idempotency_key=key,
            expires_at=timezone.now() + timedelta(hours=settings.MCP_PROPOSAL_HOURS),
        )
    except IntegrityError as exc:
        raise ToolError("Proposta repetida com a mesma chave; consulte seus rascunhos.") from exc
    except DraftValidationError as exc:
        detail = f" Campos: {json.dumps(exc.errors, ensure_ascii=False)}" if exc.errors else ""
        raise ToolError(f"{exc.messages[0]}{detail}") from exc
    except PermissionDenied as exc:
        raise ToolError(str(exc) or "Sem permissão para esta proposta.") from exc
    ctx.contract = draft.contract
    return {
        "data": draft_data(draft),
        "review_url": f"{ctx.base_url}{_draft_url(draft)}",
        "expires_at": draft.expires_at.isoformat(),
        "next_action": (
            "Proposta criada como PENDENTE; nada foi gravado. Peça à pessoa para abrir "
            "Rascunhos IA no FiscalSema, conferir o antes/depois e confirmar lá ou gerar "
            "um código de confirmação para digitar aqui (exige o escopo de executar)."
        ),
    }, 1


def _rpc_result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _json(data, status=200, headers=None):
    response = JsonResponse(data, status=status, json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    for key, value in (headers or {}).items():
        response[key] = value
    return response


def resource_metadata_url(request):
    return request.build_absolute_uri(
        reverse("oauth2_provider:oauth-resource-metadata-path", args=["mcp"])
    )


def _unauthorized(request, message, *, error="invalid_token"):
    challenge = f'Bearer error="{error}", resource_metadata="{resource_metadata_url(request)}"'
    return _json({"error": error, "error_description": message}, 401,
                 {"WWW-Authenticate": challenge})


def authenticate(request):
    """Devolve ``(token, None)`` se válido, ou ``(None, resposta_401)``."""
    from oauth2_provider.oauth2_backends import get_oauthlib_core

    if not request.headers.get("Authorization", "").lower().startswith("bearer "):
        return None, _unauthorized(request, "Conecte-se com OAuth para usar o MCP do FiscalSema.")
    valid, oauth_request = get_oauthlib_core().verify_request(request, scopes=[])
    token = getattr(oauth_request, "access_token", None) if valid else None
    if token is None or token.user_id is None or token.application_id is None:
        return None, _unauthorized(request, "Token inválido, expirado ou revogado.")
    user = token.user
    if not user.is_active or user.status != AccountStatus.ACTIVE:
        _audit(user, token.application, status=403, details={"motivo": "usuario_inativo"})
        return None, _unauthorized(request, "A conta não está ativa no FiscalSema.")
    return token, None


def _audit(user, application, *, status, tool="", contract=None, count=0, details=None):
    ApiAccessEvent.objects.create(
        event_type=ApiAccessEvent.EventType.QUERY if status < 400 else ApiAccessEvent.EventType.DENIED,
        actor=user, contract=contract, endpoint=ENDPOINT, method="POST",
        status_code=status, result_count=count,
        details={"origem": "mcp_oauth", "ferramenta": tool,
                 **(client_details(application) if application else {}), **(details or {})},
    )


def _over_limit(user):
    since = timezone.now() - timedelta(minutes=1)
    recent = ApiAccessEvent.objects.filter(actor=user, endpoint=ENDPOINT, created_at__gte=since)
    return recent.count() >= settings.MCP_PER_MINUTE


@method_decorator(csrf_exempt, name="dispatch")
class McpEndpointView(View):
    http_method_names = ["get", "post", "delete", "options"]

    def get(self, request):
        # Sem fluxo SSE do servidor: o cliente usa só POST.
        return HttpResponse(status=405, headers={"Allow": "POST"})

    def delete(self, request):
        return HttpResponse(status=405, headers={"Allow": "POST"})

    def options(self, request, *args, **kwargs):
        return HttpResponse(status=204, headers={"Allow": "POST"})

    def post(self, request):
        token, failure = authenticate(request)
        if failure:
            return failure
        if len(request.body) > MAX_BODY_BYTES:
            return _json(_rpc_error(None, -32600, "Requisição grande demais."), 413)
        try:
            message = json.loads(request.body or b"")
        except (ValueError, UnicodeDecodeError):
            return _json(_rpc_error(None, -32700, "JSON inválido."), 400)
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or "method" not in message:
            return _json(_rpc_error(None, -32600, "Requisição JSON-RPC inválida."), 400)
        if "id" not in message:
            return HttpResponse(status=202)  # notificação (ex.: notifications/initialized)
        self.base_url = request.build_absolute_uri("/").rstrip("/")
        return _json(self.handle(message, token))

    def handle(self, message, token):
        request_id, method = message["id"], message["method"]
        params = message.get("params") or {}
        if not isinstance(params, dict):
            return _rpc_error(request_id, -32602, "Parâmetros inválidos.")
        if method == "initialize":
            requested = params.get("protocolVersion")
            return _rpc_result(request_id, {
                "protocolVersion": requested if requested in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": INSTRUCTIONS,
            })
        if method == "ping":
            return _rpc_result(request_id, {})
        if method == "tools/list":
            tools = [_public(tool) for tool in TOOLS if token.allow_scopes([tool["_scope"]])]
            return _rpc_result(request_id, {"tools": tools})
        if method == "tools/call":
            return _rpc_result(request_id, self.call(params, token))
        return _rpc_error(request_id, -32601, "Método não suportado.")

    def call(self, params, token):
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        user, application = token.user, token.application
        tool = TOOLS_BY_NAME.get(name)
        if tool is None or not isinstance(arguments, dict):
            return _tool_error("Ferramenta ou argumentos inválidos.")
        if not token.allow_scopes([tool["_scope"]]):
            _audit(user, application, status=403, tool=name, details={"motivo": "escopo_insuficiente"})
            return _tool_error(
                "Esta conexão não tem permissão para esta ferramenta. Reconecte autorizando "
                f"o escopo '{tool['_scope']}'."
            )
        if _over_limit(user):
            _audit(user, application, status=429, tool=name, details={"motivo": "limite_por_minuto"})
            return _tool_error("Limite de chamadas por minuto atingido. Aguarde e tente de novo.")
        ctx = ToolContext(user, application, getattr(self, "base_url", ""))
        try:
            data, count = run_tool(name, arguments, ctx)
        except ToolError as exc:
            _audit(user, application, status=400, tool=name, contract=ctx.contract)
            return _tool_error(str(exc))
        _audit(user, application, status=200, tool=name, contract=ctx.contract, count=count)
        return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str)}]}


def _tool_error(message):
    return {"content": [{"type": "text", "text": message}], "isError": True}
