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

from accounts.models import UserProfile
from contracts.executive_dashboard import build_portfolio_summary
from contracts.intelligence import contract_intelligence_snapshot
from contracts.services import contracts_visible_to


ENABLED = True


def authorized_data(user, *, route="", contract_id=None):
    """Retorna somente resultados de serviços determinísticos e autorizados."""
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
                "valor_atual": str(portfolio.current_value),
                "empenhado": str(portfolio.committed_budget),
                "pago": str(portfolio.paid_value),
                "saldo_contratual": str(portfolio.contract_balance),
                "categorias": [
                    {
                        "categoria": row.label,
                        "quantidade": row.contract_count,
                        "valor_atual": str(row.current_value),
                        "empenhado": str(row.committed_budget),
                        "pago": str(row.paid_value),
                        "saldo": str(row.contract_balance),
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
                    "valor_atual": str(contract.current_value),
                    "categoria": (
                        contract.intelligence_classification.management_category
                        if hasattr(contract, "intelligence_classification")
                        else ""
                    ),
                }
                for contract in portfolio_contracts[:30]
            ],
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    snapshots = [contract_intelligence_snapshot(contract) for contract in contracts[:8]]
    if not snapshots:
        return (
            "Nenhum contrato autorizado foi encontrado neste contexto. "
            "Não forneça dados de contratos fora do escopo do usuário."
        )
    payload = {
        "origem": "Contract Intelligence Engine do backend",
        "somente_leitura": True,
        "nao_recalcular": True,
        "contratos": snapshots,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
