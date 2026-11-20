"""Dados contratuais autorizados para o Assistente Arise.

Quando forem autorizadas em sprint própria, as consultas a contratos, OS,
empenhos, prazos, pagamentos e relatórios deverão:

- passar somente pelos serviços internos (ex.: ``contracts_visible_to``,
  ``build_contract_dashboard``), nunca por SQL nem acesso direto da IA ao banco;
- respeitar o perfil ativo e as permissões do usuário;
- devolver texto resumido para o bloco ``<dados>`` do prompt
  (limite ``prompt.MAX_DATA_CHARS``);
- ser somente leitura.
"""

import json
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.http import Http404

from accounts.models import UserProfile
from contracts.executive_dashboard import build_portfolio_summary
from contracts.intelligence import contract_intelligence_snapshot
from contracts.services import contracts_visible_to

from .prompt import MAX_DATA_CHARS


ENABLED = True

NO_AUTHORIZED_CONTRACT = (
    "Nenhum contrato autorizado foi encontrado neste contexto. "
    "Não forneça dados de contratos fora do escopo do usuário."
)

# Campos monetários do snapshot. Quantidades e horas não entram aqui.
ITEM_MONEY_FIELDS = ("valor_unitario", "valor_utilizado", "saldo_financeiro")
AUXILIARY_MAX_CONTRACTS = 30
AUXILIARY_MAX_WORK_ORDERS = 25


def reais(value):
    """Escreve um valor já calculado pelo backend como "R$ 22.400,00".

    Só muda a apresentação para o modelo ler sem erro; não recalcula nada.
    Valores que não são número ficam como vieram.
    """
    try:
        number = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return value
    sign = "-" if number < 0 else ""
    integer, cents = f"{abs(number):.2f}".split(".")
    grouped = f"{int(integer):,}".replace(",", ".")
    return f"{sign}R$ {grouped},{cents}"


def _format_calculation(calculation):
    if not isinstance(calculation, dict):
        return reais(calculation)
    formatted = dict(calculation)
    if "valor" in formatted:
        formatted["valor"] = reais(formatted["valor"])
    formatted["evidencias"] = [
        {**evidence, "valor": reais(evidence["valor"])} if "valor" in evidence else evidence
        for evidence in formatted.get("evidencias", [])
    ]
    return formatted


def _format_snapshot(snapshot):
    """Copia o snapshot com os valores monetários escritos em reais."""
    formatted = dict(snapshot)
    formatted["financeiro"] = {
        key: reais(value) if key == "valor_atual" else _format_calculation(value)
        for key, value in snapshot.get("financeiro", {}).items()
    }
    formatted["itens"] = [
        {
            key: reais(value) if key in ITEM_MONEY_FIELDS else value
            for key, value in item.items()
        }
        for item in snapshot.get("itens", [])
    ]
    return formatted


def _dumps(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _auxiliary_data(user, contract_id):
    """Mesmos dados do painel da Auxiliar (Sprint 59), sem finanças do contrato."""
    from core.profile_dashboards import build_auxiliary_dashboard

    try:
        dashboard = build_auxiliary_dashboard(
            user, str(contract_id) if contract_id is not None else None
        )
    except Http404:
        return NO_AUTHORIZED_CONTRACT
    selected = dashboard["selected_contract"]
    contracts = (selected,) if selected is not None else dashboard["contracts"]
    if not contracts:
        return NO_AUTHORIZED_CONTRACT
    work_orders = []
    for row in dashboard["work_order_rows"][:AUXILIARY_MAX_WORK_ORDERS]:
        work_order = row["work_order"]
        work_orders.append({
            "numero": work_order.number,
            "contrato": work_order.contract.number,
            "situacao_os": work_order.get_status_display(),
            "abertura": work_order.opening_date.isoformat() if work_order.opening_date else "",
            "prazo": work_order.deadline.isoformat() if work_order.deadline else "Não informado",
            "acompanhamento": row["situation"].label,
            "em_atraso": row["is_overdue"],
            "horas": str(work_order.hours) if work_order.hours is not None else None,
            "quantidade": (
                f"{work_order.quantity} {work_order.unit_name}"
                if work_order.hours is None and work_order.quantity is not None
                else None
            ),
            "valor_unitario_os": reais(work_order.unit_value),
            "valor_da_os": reais(work_order.total_value),
        })
    payload = {
        "origem": "Painel da Auxiliar Administrativa do backend",
        "somente_leitura": True,
        "nao_recalcular": True,
        "escopo_do_perfil": (
            "Somente OS abertas e em atraso, horas ou quantidades, valores das OS "
            "e prazos. Saldo, valor atual, empenhado, executado, faturado e pago "
            "do contrato não estão autorizados para este perfil."
        ),
        "resumo_os_abertas": {
            "quantidade_contratos": len(contracts),
            "os_abertas": dashboard["open_count"],
            "os_em_atraso": dashboard["overdue_count"],
            "os_sem_prazo": dashboard["no_deadline_count"],
            "horas": str(dashboard["total_hours"]),
            "quantidades": [
                f"{row['quantity']} {row['unit']}" for row in dashboard["quantity_summaries"]
            ],
            "valor_das_os_abertas": reais(dashboard["total_value"]),
        },
        "contratos": [
            {"id": contract.pk, "numero": contract.number, "objeto": contract.object[:70]}
            for contract in contracts[:AUXILIARY_MAX_CONTRACTS]
        ],
        "ordens_servico_abertas": work_orders,
    }
    if len(work_orders) < dashboard["open_count"]:
        payload["observacao"] = (
            f"Lista limitada a {len(work_orders)} de {dashboard['open_count']} OS; "
            "selecione um contrato para ver as demais."
        )
    text = _dumps(payload)
    # Mantém o JSON inteiro dentro do limite do bloco <dados>.
    while len(text) > MAX_DATA_CHARS and payload["ordens_servico_abertas"]:
        payload["ordens_servico_abertas"].pop()
        payload["observacao"] = (
            f"Lista limitada a {len(payload['ordens_servico_abertas'])} de "
            f"{dashboard['open_count']} OS; selecione um contrato para ver as demais."
        )
        text = _dumps(payload)
    return text


def authorized_data(user, *, route="", contract_id=None):
    """Retorna somente resultados de serviços determinísticos e autorizados."""
    if user.profile == UserProfile.AUXILIARY_ADMINISTRATIVE:
        return _auxiliary_data(user, contract_id)
    contracts = contracts_visible_to(user).order_by("number", "pk")
    if contract_id is not None:
        contracts = contracts.filter(pk=contract_id)
    if user.profile == UserProfile.ADMINISTRATIVE_MANAGER and contract_id is None:
        portfolio_contracts = list(contracts.select_related("intelligence_classification"))
        portfolio = build_portfolio_summary(portfolio_contracts)
        payload = {
            "origem": "Contract Intelligence Engine do backend",
            "somente_leitura": True,
            "nao_recalcular": True,
            "carteira_institucional": {
                "quantidade_contratos": portfolio.contract_count,
                "valor_atual": reais(portfolio.current_value),
                "empenhado": reais(portfolio.committed_budget),
                "pago": reais(portfolio.paid_value),
                "saldo_contratual": reais(portfolio.contract_balance),
                "categorias": [
                    {
                        "categoria": row.label,
                        "quantidade": row.contract_count,
                        "valor_atual": reais(row.current_value),
                        "empenhado": reais(row.committed_budget),
                        "pago": reais(row.paid_value),
                        "saldo": reais(row.contract_balance),
                        "a_conferir": row.inconsistent_count,
                    }
                    for row in portfolio.categories
                ],
            },
            "contratos": [
                {
                    "id": contract.pk,
                    "numero": contract.number,
                    "fornecedor": contract.supplier_name,
                    "status": contract.status,
                    "valor_atual": reais(contract.current_value),
                    "categoria": (
                        contract.intelligence_classification.management_category
                        if hasattr(contract, "intelligence_classification")
                        else ""
                    ),
                }
                for contract in portfolio_contracts[:30]
            ],
        }
        return _dumps(payload)

    snapshots = [
        _format_snapshot(contract_intelligence_snapshot(contract))
        for contract in contracts[:8]
    ]
    if not snapshots:
        return NO_AUTHORIZED_CONTRACT
    payload = {
        "origem": "Contract Intelligence Engine do backend",
        "somente_leitura": True,
        "nao_recalcular": True,
        "contratos": snapshots,
    }
    return _dumps(payload)
