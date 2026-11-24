"""Linha do tempo segura e somente de leitura da ficha 360 do contrato.

Os detalhes JSON dos eventos não são expostos aqui porque podem conter
retratos operacionais mais amplos que o necessário para perfis de consulta.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TimelineEntry:
    occurred_at: object
    category: str
    title: str
    reference: str
    actor: str


def _actor_label(actor):
    if actor is None:
        return "Sistema"
    return actor.full_name or actor.email


def _entry(event, *, category, reference=""):
    return TimelineEntry(
        occurred_at=event.created_at,
        category=category,
        title=event.get_event_type_display(),
        reference=reference,
        actor=_actor_label(event.actor),
    )


def build_contract_timeline(contract, *, limit=80):
    """Consolida trilhas existentes sem criar fatos ou alterar registros."""

    entries = []
    entries.extend(
        _entry(event, category="Contrato")
        for event in contract.events.select_related("actor").all()
    )
    entries.extend(
        _entry(event, category="Item", reference=f"Item {event.item.number}")
        for event in contract.item_events.select_related("actor", "item").all()
    )
    entries.extend(
        _entry(event, category="Empenho", reference=f"Empenho {event.commitment.number}")
        for event in contract.commitment_events.select_related("actor", "commitment").all()
    )
    entries.extend(
        _entry(event, category="Ordem de serviço", reference=f"OS {event.work_order.number}")
        for event in contract.work_order_events.select_related("actor", "work_order").all()
    )
    entries.extend(
        _entry(
            event,
            category="Nota fiscal",
            reference=f"NF {event.invoice.number}/{event.invoice.series}",
        )
        for event in contract.invoice_events.select_related("actor", "invoice").all()
    )
    entries.extend(
        _entry(
            event,
            category="Pagamento",
            reference=f"NF {event.invoice.number}/{event.invoice.series}",
        )
        for event in contract.payment_events.select_related("actor", "invoice").all()
    )
    entries.extend(
        _entry(event, category="Inteligência contratual")
        for event in contract.intelligence_events.select_related("actor").all()
    )
    entries.sort(key=lambda item: item.occurred_at, reverse=True)
    return tuple(entries[:limit])
