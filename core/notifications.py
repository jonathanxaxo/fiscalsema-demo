"""Notificações do topo (sino): pendências dos contratos, uma a uma.

Recurso trazido do sistema principal e adaptado à demonstração (Sprint 14).
Não cria regra nova: cada aviso vem dos mesmos cálculos de
`build_contract_dashboard`. Somente leitura; não grava dados.

- Administrador: apenas solicitações de cadastro pendentes.
- Demais perfis: contratos visíveis, ativos ou suspensos. Dentro das telas de
  um contrato, somente aquele contrato é considerado, para que dados de
  contratos diferentes não se misturem.
- Quem pode alterar o contrato é levado ao registro exato para corrigir (OS,
  NF, empenho, item ou contrato). Quem só consulta é levado ao painel
  individual do contrato.
"""

from django.urls import reverse
from django.utils.formats import number_format

from accounts.models import (
    ADMINISTRATOR_PROFILES,
    RegistrationRequest,
    RegistrationStatus,
    UserProfile,
)

MAX_LISTED_NOTIFICATIONS = 30


def _money(value):
    return "R$\u00a0" + number_format(value, decimal_pos=2, use_l10n=True, force_grouping=True)


def _percent(value):
    return number_format(value, decimal_pos=2, use_l10n=True) + "%"


def _date(value):
    return f"{value:%d/%m/%Y}"


def _plural(count, singular, plural):
    return f"{count} {singular if count == 1 else plural}"


def _contract_notifications(contract, dashboard, *, can_fix):
    pk = contract.pk
    panel_url = reverse("contracts:dashboard", args=[pk])
    label = f"Contrato {contract.number}"
    entries = []

    def add(level, title, url, hint):
        entries.append(
            {
                "level": level,
                "title": title,
                "contract": label,
                "url": url if can_fix else panel_url,
                "hint": hint if can_fix else "Ver no painel do contrato",
            }
        )

    def work_order_url(work_order):
        return reverse("contracts:work_order_detail", args=[pk, work_order.pk])

    def invoice_url(invoice):
        return reverse("contracts:invoice_detail", args=[pk, invoice.work_order_id, invoice.pk])

    if dashboard.contract_is_expired:
        add(
            "danger",
            f"A vigência do contrato terminou em {_date(contract.validity_end)}",
            reverse("contracts:detail", args=[pk]),
            "Abrir contrato",
        )
    for work_order in dashboard.overdue_work_orders:
        add(
            "danger",
            f"OS {work_order.number} em atraso: prazo contratual vencido ({_date(work_order.deadline)})",
            work_order_url(work_order),
            "Abrir OS para atualizar",
        )
    for alert in dashboard.factory_deadline_alerts:
        work_order = alert.work_order
        if alert.is_overdue:
            title = (f"Cobrar a fábrica: OS {work_order.number} com prazo da fábrica "
                     f"vencido ({_date(alert.deadline)})")
        elif alert.days == 0:
            title = f"Cobrar a fábrica: OS {work_order.number} com entrega prevista para hoje"
        else:
            dias = "1 dia" if alert.days == 1 else f"{alert.days} dias"
            title = (f"Cobrar a fábrica: OS {work_order.number} com entrega em {dias} "
                     f"({_date(alert.deadline)})")
        add("danger" if alert.is_overdue else "warning", title, work_order_url(work_order),
            "Abrir OS para cobrar")
    for invoice in dashboard.dimensioned_divergences:
        add("danger",
            f"NF {invoice.number}/{invoice.series} com valor diferente do dimensionado "
            f"({_money(invoice.gross_value)} × {_money(invoice.dimensioned_value)})",
            invoice_url(invoice), "Abrir NF para devolver")
    for invoice in dashboard.returned_awaiting_correction:
        add("warning",
            f"NF {invoice.number}/{invoice.series} devolvida em {_date(invoice.returned_at)}: "
            "aguardando NF corrigida da fábrica",
            invoice_url(invoice), "Abrir NF devolvida")
    for work_order, count in dashboard.accepted_without_homologation:
        add("warning",
            f"OS {work_order.number}: {_plural(count, 'serviço aceito', 'serviços aceitos')} sem Termo de Homologação",
            work_order_url(work_order), "Abrir OS para homologar")
    for work_order, count in dashboard.homologated_without_invoice:
        add("warning",
            f"OS {work_order.number}: {_plural(count, 'serviço homologado', 'serviços homologados')} sem NF",
            work_order_url(work_order), "Abrir OS para conferir o faturamento")
    for attention in dashboard.divergent_invoices:
        invoice = attention.invoice
        add(
            "danger",
            f"NF {invoice.number}/{invoice.series} {attention.status_label.lower()}",
            invoice_url(invoice),
            "Abrir NF para conferir",
        )
    if dashboard.item_total != contract.current_value:
        add(
            "warning",
            f"A soma dos itens ({_money(dashboard.item_total)}) diverge do valor atual "
            f"do contrato ({_money(contract.current_value)})",
            reverse("contracts:item_list", args=[pk]),
            "Abrir itens para conferir",
        )
    if dashboard.contract_balance_is_low:
        add(
            "warning",
            f"Saldo contratual abaixo de 20%: {_percent(dashboard.contract_balance_percentage)} disponível",
            reverse("contracts:detail", args=[pk]),
            "Abrir contrato",
        )
    for entry in dashboard.invoice_financial_deadlines:
        invoice = entry.invoice
        situation = "vencido" if entry.is_overdue else "a conferir"
        add(
            "danger" if entry.is_overdue else "warning",
            f"Prazo de encaminhamento da NF {invoice.number}/{invoice.series}: "
            f"{_date(entry.deadline)} ({situation})",
            invoice_url(invoice),
            "Abrir NF",
        )
    for alert in dashboard.low_commitments:
        add(
            "warning",
            f"Empenho {alert.commitment.number} com saldo de {_money(alert.available)} "
            f"({_percent(alert.percentage)})",
            reverse("contracts:commitment_detail", args=[pk, alert.commitment.pk]),
            "Abrir empenho",
        )
    for alert in dashboard.low_hour_items:
        add(
            "warning",
            f"Item por hora {alert.item.number} com saldo abaixo de 20% "
            f"({_percent(alert.percentage)})",
            reverse("contracts:item_detail", args=[pk, alert.item.pk]),
            "Abrir item",
        )
    for work_order in dashboard.work_orders_without_allocation:
        add(
            "warning",
            f"OS {work_order.number} sem rateio ativo",
            work_order_url(work_order),
            "Abrir OS para cadastrar o rateio",
        )
    for work_order in dashboard.completed_work_orders_without_invoice:
        add(
            "warning",
            f"OS {work_order.number} concluída sem NF",
            work_order_url(work_order),
            "Abrir OS para cadastrar a NF",
        )
    for attention in dashboard.pending_invoices:
        invoice = attention.invoice
        add(
            "warning",
            f"NF {invoice.number}/{invoice.series} pendente de conferência",
            invoice_url(invoice),
            "Abrir NF para conferir",
        )
    # Acompanhamento mensal (Sprint 19): só o que ainda pede ação; o verde não notifica.
    for monthly in dashboard.monthly_work_order_attentions:
        if monthly.tone == "success":
            continue
        add(
            monthly.tone,
            f"OS {monthly.work_order.number} (mensal) — competência {monthly.competence}: "
            f"{monthly.state}",
            work_order_url(monthly.work_order),
            "Abrir OS para atualizar o mês",
        )
    return entries


def build_notifications(user, *, contract_id=None):
    from contracts.dashboard import build_contract_dashboard
    from contracts.models import (
        ContractFindingSeverity,
        ContractFindingStatus,
        ContractStatus,
    )
    from contracts.services import contracts_visible_to, contracts_writable_by

    entries = []
    if user.has_perm("accounts.review_registration"):
        pending = RegistrationRequest.objects.filter(status=RegistrationStatus.PENDING).count()
        if pending:
            entries.append(
                {
                    "level": "warning",
                    "title": _plural(
                        pending,
                        "solicitação de cadastro pendente",
                        "solicitações de cadastro pendentes",
                    ),
                    "contract": "Administração",
                    "url": reverse("accounts_admin:registration_list"),
                    "hint": "Abrir solicitações",
                }
            )

    if user.profile == UserProfile.AUXILIARY_ADMINISTRATIVE:
        from .profile_dashboards import build_auxiliary_dashboard

        dashboard = build_auxiliary_dashboard(user)
        for row in dashboard["rows"]:
            contract = row["contract"]
            if contract_id is not None and contract.pk != contract_id:
                continue
            for issue in row["issues"]:
                entries.append(
                    {
                        "level": "warning",
                        "title": issue,
                        "contract": f"Contrato {contract.number}",
                        "url": reverse("home") + "#aux-cadastros",
                        "hint": "Conferir metadados administrativos",
                    }
                )
    elif user.profile not in ADMINISTRATOR_PROFILES:
        contracts = contracts_visible_to(user).filter(
            status__in=(ContractStatus.ACTIVE, ContractStatus.SUSPENDED)
        ).order_by("number", "pk")
        if contract_id is not None:
            contracts = contracts.filter(pk=contract_id)
        writable_ids = set(contracts_writable_by(user).values_list("pk", flat=True))
        for contract in contracts:
            entries.extend(
                _contract_notifications(
                    contract,
                    build_contract_dashboard(contract),
                    can_fix=contract.pk in writable_ids,
                )
            )
            for finding in contract.intelligence_findings.filter(
                status__in=(
                    ContractFindingStatus.NEW,
                    ContractFindingStatus.READ,
                    ContractFindingStatus.IN_ANALYSIS,
                    ContractFindingStatus.AWAITING_INFORMATION,
                )
            ).order_by("-last_detected_at", "pk"):
                entries.append(
                    {
                        "level": (
                            "danger"
                            if finding.severity == ContractFindingSeverity.CRITICAL
                            else "warning"
                        ),
                        "title": finding.title,
                        "contract": f"Contrato {contract.number}",
                        "url": reverse(
                            "contracts:intelligence", kwargs={"contract_pk": contract.pk}
                        ),
                        "hint": "Analisar pendência",
                    }
                )

    # Itens críticos primeiro, preservando a ordem de cálculo dentro de cada nível.
    entries.sort(key=lambda entry: 0 if entry["level"] == "danger" else 1)
    return {
        "count": len(entries),
        "items": entries[:MAX_LISTED_NOTIFICATIONS],
        "hidden_count": max(len(entries) - MAX_LISTED_NOTIFICATIONS, 0),
    }
