#!/usr/bin/env python3
"""Adaptador MCP do FiscalSema Demo.

O processo usa somente a API HTTP autorizada. Não importa Django, não acessa
modelos e não abre conexão com o banco. O token é lido exclusivamente da
variável FISCALSEMA_API_TOKEN e nunca é devolvido em respostas ou logs.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "fiscalsema-demo", "version": "1.0.0"}

QUERY_TOOLS = {
    "listar_contratos_autorizados": "/api/v1/contracts/",
    "consultar_resumo_contrato": "/api/v1/contracts/{contract_id}/summary/",
    "consultar_itens": "/api/v1/contracts/{contract_id}/items/",
    "consultar_empenhos": "/api/v1/contracts/{contract_id}/commitments/",
    "consultar_ordens_servico": "/api/v1/contracts/{contract_id}/work-orders/",
    "consultar_notas_fiscais": "/api/v1/contracts/{contract_id}/invoices/",
    "consultar_pendencias": "/api/v1/contracts/{contract_id}/accountability/",
}

TOOLS = [
    {
        "name": "listar_contratos_autorizados",
        "description": "Lista somente os contratos permitidos à credencial.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "page": {"type": "integer", "minimum": 1},
                "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
            },
            "additionalProperties": False,
        },
    },
    *[
        {
            "name": name,
            "description": description,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contract_id": {"type": "integer", "minimum": 1},
                    "page": {"type": "integer", "minimum": 1},
                    "page_size": {"type": "integer", "minimum": 1, "maximum": 100},
                },
                "required": ["contract_id"],
                "additionalProperties": False,
            },
        }
        for name, description in (
            ("consultar_resumo_contrato", "Consulta o resumo autorizado do contrato."),
            ("consultar_itens", "Consulta itens do contrato autorizado."),
            ("consultar_empenhos", "Consulta empenhos do contrato autorizado."),
            ("consultar_ordens_servico", "Consulta ordens de serviço do contrato autorizado."),
            ("consultar_notas_fiscais", "Consulta notas fiscais do contrato autorizado."),
            ("consultar_pendencias", "Consulta a prestação de contas e pendências autorizadas."),
        )
    ],
    {
        "name": "propor_rascunho",
        "description": (
            "Cria somente uma proposta pendente. Não executa, confirma, rejeita "
            "nem altera diretamente um registro operacional."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["CONTRATO", "ITEM", "EMPENHO", "OS", "RATEIO", "EXECUCAO", "NF", "PAGAMENTO"],
                },
                "operation": {"type": "string", "enum": ["CRIAR", "ATUALIZAR"]},
                "context": {"type": "object"},
                "payload": {"type": "object"},
                "source_summary": {"type": "string", "minLength": 1},
                "source_authority": {
                    "type": "string",
                    "enum": ["DOCUMENTO_OFICIAL_VALIDADO", "IMPORTACAO_CONFIRMADA", "EXTRACAO_AUTOMATICA"],
                },
                "confidence_level": {
                    "type": "string",
                    "enum": ["CONFIRMADO", "ENCONTRADO_EM_FONTE", "INFERIDO", "ESTIMADO", "PENDENTE", "DIVERGENTE"],
                },
                "evidence": {"type": "array", "items": {"type": "object"}, "minItems": 1},
            },
            "required": [
                "entity_type", "operation", "context", "payload",
                "source_summary", "source_authority", "confidence_level", "evidence",
            ],
            "additionalProperties": False,
        },
    },
]


class McpError(Exception):
    """Erro seguro apresentado ao cliente MCP."""


class ApiClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or os.getenv("FISCALSEMA_API_URL", "")).rstrip("/")
        self.token = token or os.getenv("FISCALSEMA_API_TOKEN", "")
        if not self.base_url:
            raise McpError("Configure FISCALSEMA_API_URL.")
        if not self.token:
            raise McpError("Configure FISCALSEMA_API_TOKEN fora do repositório.")

    def request(
        self, method: str, path: str, *, query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            clean_query = {key: value for key, value in query.items() if value is not None}
            if clean_query:
                url = f"{url}?{urlencode(clean_query)}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "FiscalSema-Demo-MCP/1.0",
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode("utf-8"))
                message = detail.get("error", {}).get("message", "Requisição recusada.")
            except (ValueError, AttributeError):
                message = "Requisição recusada."
            raise McpError(f"API recusou a operação ({exc.code}): {message}") from None
        except (URLError, TimeoutError):
            raise McpError("Não foi possível alcançar a API do ambiente demonstrativo.") from None


def _positive_int(arguments: dict[str, Any], key: str, *, required: bool = False) -> int | None:
    value = arguments.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise McpError(f"{key} deve ser um número inteiro positivo.")
    return value


def call_tool(name: str, arguments: dict[str, Any], client: ApiClient) -> dict[str, Any]:
    if name in QUERY_TOOLS:
        contract_id = None
        if "{contract_id}" in QUERY_TOOLS[name]:
            contract_id = _positive_int(arguments, "contract_id", required=True)
        page = _positive_int(arguments, "page")
        page_size = _positive_int(arguments, "page_size")
        if page_size is not None and page_size > 100:
            raise McpError("page_size deve ser no máximo 100.")
        path = QUERY_TOOLS[name]
        if contract_id is not None:
            path = path.format(contract_id=contract_id)
        result = client.request(
            "GET", path, query={"page": page, "page_size": page_size},
        )
        return {
            "ferramenta": name,
            "somente_leitura": True,
            "executada": False,
            "resultado": result,
        }

    if name == "propor_rascunho":
        result = client.request("POST", "/api/v1/drafts/", body=arguments)
        return {
            "ferramenta": name,
            "proposta_criada": True,
            "executada": False,
            "requer_aprovacao_humana": True,
            "mensagem": (
                "A proposta foi registrada como rascunho. Nenhum dado "
                "operacional foi alterado."
            ),
            "rascunho": result,
        }

    raise McpError("Ferramenta inexistente ou não autorizada.")


def result_content(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ],
        "structuredContent": payload,
        "isError": False,
    }


def handle_message(message: dict[str, Any], client_factory=ApiClient) -> dict[str, Any] | None:
    method = message.get("method")
    request_id = message.get("id")
    if request_id is None:
        return None
    try:
        if method == "initialize":
            payload = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
                "instructions": (
                    "Use somente dados fictícios. Consultas são limitadas pela API. "
                    "Propostas nunca são executadas sem revisão humana na interface."
                ),
            }
        elif method == "tools/list":
            payload = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params") or {}
            arguments = params.get("arguments") or {}
            if not isinstance(arguments, dict):
                raise McpError("arguments deve ser um objeto JSON.")
            payload = result_content(
                call_tool(params.get("name", ""), arguments, client_factory())
            )
        elif method == "ping":
            payload = {}
        else:
            raise McpError("Método MCP não suportado.")
        return {"jsonrpc": "2.0", "id": request_id, "result": payload}
    except McpError as exc:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            response = handle_message(message)
        except (ValueError, TypeError):
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "JSON inválido."},
            }
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
