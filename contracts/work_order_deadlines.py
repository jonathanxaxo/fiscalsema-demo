"""Prazos da Ordem de Serviço (Sprint 36; referência: FiscalSema Light).

Dois prazos convivem na OS:

- **prazo contratual** (``deadline``): sugerido como abertura + 6 meses; é o
  que define o **atraso** da OS;
- **prazo de entrega da fábrica** (``factory_deadline``): data estipulada pela
  fábrica; serve para **cobrar** a entrega (aviso 7 dias antes e após vencer).

Somente classifica datas já informadas: não grava nada nem altera cálculos.
"""

import calendar
from dataclasses import dataclass
from datetime import date

from .models import WorkOrderStatus

DEFAULT_DEADLINE_MONTHS = 6
FACTORY_NOTICE_DAYS = 7

OPEN_STATUSES = frozenset({
    WorkOrderStatus.OPEN, WorkOrderStatus.SIGNED,
    WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.SUSPENDED,
})
OPEN_CODES = frozenset({"on_time", "factory_due", "factory_overdue", "late"})


def suggested_deadline(opening_date, months=DEFAULT_DEADLINE_MONTHS):
    """Mesmo dia, N meses depois; se o dia não existir no mês, usa o último dia."""
    month_index = opening_date.month - 1 + months
    year = opening_date.year + month_index // 12
    month = month_index % 12 + 1
    return opening_date.replace(
        year=year, month=month, day=min(opening_date.day, calendar.monthrange(year, month)[1]),
    )


def _plural(days):
    days = abs(days)
    return "1 dia" if days == 1 else f"{days} dias"


@dataclass(frozen=True)
class Countdown:
    text: str
    tone: str


def countdown(days):
    """"faltam N dias" / "vence hoje" / "vencido há N dias", com a cor da situação."""
    if days is None:
        return Countdown("não informado", "neutral")
    if days < 0:
        return Countdown(f"vencido há {_plural(days)}", "danger")
    if days == 0:
        return Countdown("vence hoje", "warning")
    text = "falta 1 dia" if days == 1 else f"faltam {days} dias"
    return Countdown(text, "warning" if days <= FACTORY_NOTICE_DAYS else "success")


@dataclass(frozen=True)
class DeadlineSituation:
    code: str
    label: str
    tone: str
    contract_days: int | None
    factory_days: int | None

    @property
    def is_open(self):
        return self.code in OPEN_CODES

    @property
    def contract_countdown(self):
        return countdown(self.contract_days) if self.is_open else None

    @property
    def factory_countdown(self):
        return countdown(self.factory_days) if self.is_open else None


def _days(target, today):
    return None if target is None else (target - today).days


def deadline_situation(work_order, today: date) -> DeadlineSituation:
    contract_days = _days(work_order.deadline, today)
    factory_days = _days(work_order.factory_deadline, today)

    def result(code, label, tone):
        return DeadlineSituation(code, label, tone, contract_days, factory_days)

    status = work_order.status
    if status == WorkOrderStatus.CANCELED:
        return result("canceled", "Cancelada", "neutral")
    if status == WorkOrderStatus.COMPLETED:
        delivered = work_order.completion_date
        if delivered and work_order.deadline and delivered > work_order.deadline:
            return result("delivered_late", "Entregue com atraso", "warning")
        return result("delivered", "Entregue", "success")
    if status not in OPEN_STATUSES:
        return result("other", work_order.get_status_display(), "neutral")
    if contract_days is not None and contract_days < 0:
        return result("late", f"Em atraso há {_plural(contract_days)} (prazo contratual)", "danger")
    if factory_days is not None and factory_days < 0:
        return result(
            "factory_overdue", f"Cobrar a fábrica: prazo da fábrica vencido há {_plural(factory_days)}",
            "danger",
        )
    if factory_days is not None and factory_days <= FACTORY_NOTICE_DAYS:
        when = "hoje" if factory_days == 0 else f"em {_plural(factory_days)}"
        return result("factory_due", f"Cobrar a fábrica: entrega {when}", "warning")
    return result("on_time", "No prazo", "success")
