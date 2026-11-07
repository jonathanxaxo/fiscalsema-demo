"""Preenche um contrato da demo com dados fictícios de apresentação.

Exceção autorizada pelo responsável à regra de não criar dados fictícios
automaticamente. Usa somente os serviços de negócio do sistema (mesmas
validações, permissões e auditoria da tela). Valores e datas são calculados a
partir do saldo e da vigência do próprio contrato. É idempotente: se os itens
de demonstração já existirem, nada é alterado.
"""

import os
from datetime import timedelta
from decimal import ROUND_DOWN, Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from contracts.models import (
    Contract,
    ContractItem,
    ContractItemUnit,
    WorkOrderAllocationStatus,
    WorkOrderStatus,
)
from contracts.services import (
    contract_financial_position,
    create_budget_commitment,
    create_contract_item,
    create_invoice,
    create_payment,
    create_work_order,
    create_work_order_allocation,
    create_work_order_execution,
)

MARKER = "[DEMO-APRESENTACAO]"
CENT = Decimal("0.01")
MIN_BUDGET = Decimal("3000.00")


def _money(value):
    return value.quantize(CENT, rounding=ROUND_DOWN)


def _competence(day):
    return day.strftime("%m/%Y")


def presentation_timeline(contract, today):
    """Datas da apresentação: histórico entre o início da janela e hoje; prazos no futuro.

    Nenhuma data de execução, Nota Fiscal ou pagamento fica depois de hoje.
    """
    end = contract.validity_end
    window_start = max(contract.validity_start, today - timedelta(days=75))
    last_day = min(today, end)
    span = max((last_day - window_start).days, 0)

    def past(fraction):
        return window_start + timedelta(days=round(span * fraction))

    def future(days):
        return max(min(today + timedelta(days=days), end), last_day)

    return {
        "commitment": past(0),
        "os01": {"opening": past(0.05), "signature": past(0.05), "start": past(0.10),
                 "deadline": past(0.70), "completion": past(0.60)},
        "os01_execution": past(0.60),
        "os01_invoice": past(0.65),
        "os01_payment": past(0.90),
        "os02": {"opening": past(0.40), "signature": past(0.40), "start": past(0.45),
                 "deadline": future(30)},
        "os02_execution": past(0.80),
        "os02_invoice": past(0.85),
        "os03": {"opening": past(0.15), "signature": past(0.15), "start": past(0.20),
                 "deadline": past(0.50)},
        "os04": {"opening": last_day, "signature": last_day, "deadline": future(45)},
        "os05": {"opening": last_day, "deadline": future(60)},
    }


class Command(BaseCommand):
    help = "Preenche um contrato da demo com itens, empenhos, OS, execuções, NFs e pagamento fictícios."

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Operação recusada: comando exclusivo do ambiente demo.")
        number = os.getenv("DEMO_CONTRACT_NUMBER", "").strip()
        fiscal_email = os.getenv("DEMO_FISCAL_EMAIL", "").strip()
        if not number or not fiscal_email:
            raise CommandError("Defina DEMO_CONTRACT_NUMBER e DEMO_FISCAL_EMAIL.")

        fiscal = User.objects.filter(
            email__iexact=User.objects.normalize_login_email(fiscal_email)
        ).first()
        contracts = Contract.objects.filter(number=number, archived_at__isnull=True)
        if fiscal is None or contracts.filter(responsible_fiscal=fiscal).count() != 1:
            raise CommandError(
                "Operação recusada: o contrato informado não pertence a esse Fiscal ou não é único."
            )
        contract = contracts.get(responsible_fiscal=fiscal)

        if ContractItem.objects.filter(contract=contract, number="DEMO-1").exists():
            self.stdout.write("Dados de apresentação já existem neste contrato; nada foi alterado.")
            return

        balance = contract_financial_position(contract).contract_balance.value
        budget = _money(balance * Decimal("0.5"))
        if budget < MIN_BUDGET:
            raise CommandError("Operação recusada: saldo do contrato insuficiente para os dados de apresentação.")

        timeline = presentation_timeline(contract, timezone.localdate())

        with transaction.atomic():
            self._seed(contract, fiscal, budget, timeline)

        self.stdout.write(self.style.SUCCESS("Dados de apresentação criados com segurança."))

    def _seed(self, contract, actor, budget, t):
        note = f"{MARKER} Dado fictício para apresentação."
        items_spec = [
            ("DEMO-1", "Suporte técnico especializado", ContractItemUnit.HOUR, Decimal("200.00"), Decimal("0.45")),
            ("DEMO-2", "Manutenção corretiva de sistemas", ContractItemUnit.HOUR, Decimal("150.00"), Decimal("0.35")),
            ("DEMO-3", "Licença de software de gestão", ContractItemUnit.UNIT, Decimal("1000.00"), Decimal("0.20")),
        ]
        items = {}
        for code, description, unit, unit_value, share in items_spec:
            quantity = (budget * share / unit_value).quantize(Decimal("1"), rounding=ROUND_DOWN)
            if quantity < 4:
                raise CommandError("Operação recusada: saldo do contrato insuficiente para os itens.")
            items[code] = create_contract_item(
                contract_id=contract.pk,
                actor=actor,
                number=code,
                external_code="",
                description=description,
                category="Serviços (fictício)",
                unit=unit,
                custom_unit_name="",
                contracted_quantity=quantity,
                unit_value=unit_value,
                calculation_rule="",
                source_reference=MARKER,
                is_active=True,
            )

        commitments = [
            create_budget_commitment(
                contract_id=contract.pk,
                actor=actor,
                number=f"{t['commitment'].year}NE90000{index}",
                ped=f"{t['commitment'].year}PD90000{index}",
                commitment_date=t["commitment"],
                initial_value=_money(budget * share),
                source="Fonte fictícia de demonstração",
                notes=note,
                is_active=True,
            )
            for index, share in ((1, Decimal("0.40")), (2, Decimal("0.30")))
        ]

        def hours_for(item, fraction):
            return (item.contracted_quantity * fraction).quantize(Decimal("1"), rounding=ROUND_DOWN)

        def order(number, item, fraction, status, opening, deadline, **extra):
            measure = hours_for(item, fraction)
            data = {
                "number": number,
                "item": item,
                "description": f"{item.description} — {MARKER}",
                "quantity": measure if item.unit == ContractItemUnit.UNIT else None,
                "hours": measure if item.unit != ContractItemUnit.UNIT else None,
                "responsible": "Equipe fictícia de demonstração",
                "opening_date": opening,
                "signature_date": None,
                "start_date": None,
                "deadline": deadline,
                "completion_date": None,
                "status": status,
                "process_number": f"PROC-{number}",
                "notes": note,
            }
            data.update(extra)
            return create_work_order(contract_id=contract.pk, actor=actor, **data)

        def allocate(work_order, commitment):
            return create_work_order_allocation(
                work_order_id=work_order.pk,
                actor=actor,
                commitment=commitment,
                amount=work_order.total_value,
                allocation_date=work_order.opening_date,
                status=WorkOrderAllocationStatus.ACTIVE,
            )

        def execute(work_order, fraction, when):
            measure = (work_order.measure * fraction).quantize(Decimal("1"), rounding=ROUND_DOWN)
            return create_work_order_execution(
                work_order_id=work_order.pk,
                actor=actor,
                executed_quantity=measure,
                executed_value=_money(measure * work_order.unit_value),
                execution_date=when,
                competence=_competence(when),
                notes=note,
                evidence_reference="Relatório fictício de execução",
            )

        def invoice(work_order, number, value, when):
            return create_invoice(
                work_order_id=work_order.pk,
                actor=actor,
                item=None,
                allocation=None,
                number=number,
                series="DEMO",
                supplier_name=contract.supplier_name,
                supplier_tax_id=contract.supplier_tax_id,
                issue_date=when,
                competence=_competence(when),
                gross_value=value,
                deduction_value=Decimal("0.00"),
                accepted_value=value,
                process_number=f"PROC-{number}",
                status="Recebida",
                document_reference="Documento fiscal fictício",
                document_hash="",
                notes=note,
            )

        item1, item2, item3 = items["DEMO-1"], items["DEMO-2"], items["DEMO-3"]

        completed = order(
            "DEMO-OS-01", item1, Decimal("0.20"), WorkOrderStatus.COMPLETED,
            t["os01"]["opening"], t["os01"]["deadline"], signature_date=t["os01"]["signature"],
            start_date=t["os01"]["start"], completion_date=t["os01"]["completion"],
        )
        allocate(completed, commitments[0])
        execute(completed, Decimal("1"), t["os01_execution"])
        nf_paid = invoice(completed, "DEMO-NF-01", completed.total_value, t["os01_invoice"])
        create_payment(
            invoice_id=nf_paid.pk,
            actor=actor,
            amount=nf_paid.accepted_value,
            payment_date=t["os01_payment"],
            competence=_competence(t["os01_payment"]),
            status="Pago conforme fonte",
            process_number="PROC-DEMO-PAG-01",
            attestation_reference="Atesto fictício 01",
            raer_reference="RAER fictício 01",
            homologation_reference="Termo fictício 01",
            evidence_reference="Comprovante fictício 01",
            notes=note,
        )

        in_progress = order(
            "DEMO-OS-02", item2, Decimal("0.25"), WorkOrderStatus.IN_PROGRESS,
            t["os02"]["opening"], t["os02"]["deadline"], signature_date=t["os02"]["signature"],
            start_date=t["os02"]["start"],
        )
        allocate(in_progress, commitments[1])
        partial = execute(in_progress, Decimal("0.5"), t["os02_execution"])
        invoice(in_progress, "DEMO-NF-02", partial.executed_value, t["os02_invoice"])

        order(
            "DEMO-OS-03", item1, Decimal("0.15"), WorkOrderStatus.IN_PROGRESS,
            t["os03"]["opening"], t["os03"]["deadline"], signature_date=t["os03"]["signature"],
            start_date=t["os03"]["start"],
        )
        order(
            "DEMO-OS-04", item3, Decimal("0.25"), WorkOrderStatus.SIGNED,
            t["os04"]["opening"], t["os04"]["deadline"], signature_date=t["os04"]["signature"],
        )
        order(
            "DEMO-OS-05", item2, Decimal("0.10"), WorkOrderStatus.DRAFT,
            t["os05"]["opening"], t["os05"]["deadline"],
        )
