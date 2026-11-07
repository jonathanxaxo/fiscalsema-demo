"""Corrige as datas dos dados fictícios de apresentação que ficaram no futuro.

Usa somente as funções de edição do sistema (mesmas validações e auditoria da
tela). Só atua quando existe alguma data histórica de demonstração depois de
hoje; caso contrário, nada é alterado.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from contracts.models import (
    BudgetCommitment,
    Contract,
    Invoice,
    Payment,
    WorkOrder,
    WorkOrderAllocation,
    WorkOrderAllocationStatus,
    WorkOrderExecution,
)
from contracts.services import (
    update_budget_commitment,
    update_invoice,
    update_payment,
    update_work_order,
    update_work_order_allocation,
    update_work_order_execution,
)

from .seed_demo_presentation import MARKER, _competence, presentation_timeline


class Command(BaseCommand):
    help = "Move para o passado as datas históricas dos dados fictícios de apresentação."

    def handle(self, *args, **options):
        if getattr(settings, "APP_ENVIRONMENT", "") != "demo":
            raise CommandError("Operação recusada: comando exclusivo do ambiente demo.")
        number = os.getenv("DEMO_CONTRACT_NUMBER", "").strip()
        fiscal_email = os.getenv("DEMO_FISCAL_EMAIL", "").strip()
        if not number or not fiscal_email:
            raise CommandError("Defina DEMO_CONTRACT_NUMBER e DEMO_FISCAL_EMAIL.")
        actor = User.objects.filter(
            email__iexact=User.objects.normalize_login_email(fiscal_email)
        ).first()
        contract = Contract.objects.filter(
            number=number, archived_at__isnull=True, responsible_fiscal=actor
        ).first() if actor else None
        if contract is None:
            raise CommandError("Operação recusada: contrato não encontrado para esse Fiscal.")

        orders = {o.number: o for o in WorkOrder.objects.filter(contract=contract, number__startswith="DEMO-OS-")}
        if len(orders) != 5:
            raise CommandError("Operação recusada: dados de apresentação não encontrados neste contrato.")
        executions = WorkOrderExecution.objects.filter(work_order__in=orders.values())
        invoices = {i.number: i for i in Invoice.objects.filter(contract=contract, number__startswith="DEMO-NF-")}
        payments = Payment.objects.filter(invoice__in=invoices.values())

        today = timezone.localdate()
        historical = [e.execution_date for e in executions]
        historical += [i.issue_date for i in invoices.values()]
        historical += [p.payment_date for p in payments]
        historical += [o.completion_date for o in orders.values() if o.completion_date]
        if all(value <= today for value in historical):
            self.stdout.write("Nenhuma data de demonstração está no futuro; nada foi alterado.")
            return

        t = presentation_timeline(contract, today)
        with transaction.atomic():
            for commitment in BudgetCommitment.objects.filter(contract=contract, notes__contains=MARKER):
                update_budget_commitment(
                    commitment_id=commitment.pk, actor=actor, commitment_date=t["commitment"]
                )
            plan = {"DEMO-OS-01": "os01", "DEMO-OS-02": "os02", "DEMO-OS-03": "os03", "DEMO-OS-04": "os04", "DEMO-OS-05": "os05"}
            for os_number, key in plan.items():
                dates = t[key]
                work_order = orders[os_number]
                changes = {
                    "item": work_order.item,
                    "opening_date": dates["opening"],
                    "deadline": dates["deadline"],
                }
                for source, field in (("signature", "signature_date"), ("start", "start_date"), ("completion", "completion_date")):
                    if source in dates:
                        changes[field] = dates[source]
                update_work_order(work_order_id=work_order.pk, actor=actor, **changes)
            for allocation in WorkOrderAllocation.objects.filter(
                work_order__in=orders.values(), status=WorkOrderAllocationStatus.ACTIVE
            ).select_related("work_order", "commitment"):
                update_work_order_allocation(
                    allocation_id=allocation.pk,
                    actor=actor,
                    commitment=allocation.commitment,
                    allocation_date=t[plan[allocation.work_order.number]]["opening"],
                )
            execution_dates = {"DEMO-OS-01": t["os01_execution"], "DEMO-OS-02": t["os02_execution"]}
            for execution in executions.select_related("work_order"):
                when = execution_dates[execution.work_order.number]
                update_work_order_execution(
                    execution_id=execution.pk, actor=actor, execution_date=when, competence=_competence(when)
                )
            invoice_dates = {"DEMO-NF-01": t["os01_invoice"], "DEMO-NF-02": t["os02_invoice"]}
            for number_, invoice in invoices.items():
                when = invoice_dates[number_]
                update_invoice(invoice_id=invoice.pk, actor=actor, issue_date=when, competence=_competence(when))
            for payment in payments:
                when = t["os01_payment"]
                update_payment(payment_id=payment.pk, actor=actor, payment_date=when, competence=_competence(when))

        self.stdout.write(self.style.SUCCESS("Datas dos dados de apresentação corrigidas com segurança."))
