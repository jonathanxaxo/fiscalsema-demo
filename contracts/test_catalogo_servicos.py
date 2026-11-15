"""Catálogo de serviços, memória de cálculo e ciclo do serviço na OS (Sprint 38).

Referência: FiscalSema Light (somente lido). Dados fictícios.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.utils import timezone

from .calculations import calculate_service_units
from .models import (
    ContractEvent, ContractItemUnit, ServiceComplexity, ServiceLineStatus, WorkOrderEvent,
    WorkOrderServiceLine, WorkOrderStatus,
)
from .service_catalog import (
    accept_service_line, add_work_order_service_line, create_service_catalog_entry,
    homologate_accepted_service_lines, register_service_line_delivery, reject_service_line,
    remove_work_order_service_line, update_service_catalog_entry, update_work_order_service_line,
    work_order_service_summary,
)
from .services import create_contract_item, create_work_order
from .test_items import item_data
from .test_work_orders import WorkOrderBase, work_order_data


class CatalogoBase(WorkOrderBase):
    def setUp(self):
        super().setUp()
        self.ust_item = create_contract_item(
            contract_id=self.contract.pk, actor=self.owner,
            **item_data(number="UST-1", unit=ContractItemUnit.UST, contracted_quantity=Decimal("10000"),
                        unit_value=Decimal("10.00")),
        )
        self.entry = create_service_catalog_entry(
            contract_id=self.contract.pk, actor=self.owner, code="SRV-01",
            name="Desenvolvimento de funcionalidade fictícia", measure_label="por funcionalidade",
            weight_low=Decimal("2"), weight_medium=Decimal("3.5"), weight_high=None,
            source_reference="Catálogo fictício v1",
        )
        self.today = timezone.localdate()
        self.wo = create_work_order(
            contract_id=self.contract.pk, actor=self.owner,
            **work_order_data(self.ust_item, number="OS-UST", hours=None, quantity=Decimal("1"),
                              status=WorkOrderStatus.IN_PROGRESS,
                              opening_date=self.today - timedelta(days=20),
                              deadline=self.today + timedelta(days=60)),
        )

    def add(self, complexity=ServiceComplexity.MEDIUM, quantity=Decimal("10")):
        return add_work_order_service_line(work_order_id=self.wo.pk, actor=self.owner,
                                           catalog_entry=self.entry, complexity=complexity, quantity=quantity)


class CatalogoTests(CatalogoBase):
    def test_units_formula_and_new_item_units(self):
        self.assertEqual(calculate_service_units(Decimal("95"), Decimal("3.5")), Decimal("332.5000"))
        self.assertEqual({"UST", "HST", "USN"} <= set(ContractItemUnit.values), True)

    def test_catalog_requires_a_weight_and_is_audited(self):
        with self.assertRaises(ValidationError):
            create_service_catalog_entry(contract_id=self.contract.pk, actor=self.owner, name="Sem peso",
                                         measure_label="por unidade")
        update_service_catalog_entry(entry_id=self.entry.pk, actor=self.owner, weight_medium=Decimal("4"))
        events = ContractEvent.objects.filter(contract=self.contract).values_list("event_type", flat=True)
        self.assertIn("CATALOGO_SERVICO_CRIADO", events)
        self.assertIn("CATALOGO_SERVICO_ALTERADO", events)

    def test_other_person_cannot_edit_catalog(self):
        with self.assertRaises((PermissionDenied, Exception)):
            create_service_catalog_entry(contract_id=self.contract.pk, actor=self.other, name="X",
                                         measure_label="u", weight_medium=Decimal("1"))


class MemoriaDeCalculoTests(CatalogoBase):
    def test_lines_recalculate_work_order_quantity_and_freeze_weight(self):
        line = self.add(quantity=Decimal("10"))
        self.add(complexity=ServiceComplexity.LOW, quantity=Decimal("5"))
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.quantity, Decimal("45"))  # 10×3,5 + 5×2
        self.assertEqual(self.wo.total_value, Decimal("450.00"))
        update_service_catalog_entry(entry_id=self.entry.pk, actor=self.owner, weight_medium=Decimal("9"))
        line.refresh_from_db()
        self.assertEqual(line.weight, Decimal("3.5"))  # congelado na OS
        update_work_order_service_line(line_id=line.pk, actor=self.owner,
                                       complexity=ServiceComplexity.MEDIUM, quantity=Decimal("2"))
        self.wo.refresh_from_db()
        self.assertEqual(self.wo.quantity, Decimal("17"))
        summary = work_order_service_summary(self.wo)
        self.assertTrue(summary["matches_work_order"])
        self.assertEqual(summary["total_units"], Decimal("17"))
        types = set(WorkOrderEvent.objects.filter(work_order=self.wo).values_list("event_type", flat=True))
        self.assertTrue({"SERVICO_INCLUIDO", "SERVICO_ALTERADO"} <= types)

    def test_na_complexity_inactive_service_and_hour_order_are_refused(self):
        with self.assertRaises(ValidationError):
            self.add(complexity=ServiceComplexity.HIGH)
        update_service_catalog_entry(entry_id=self.entry.pk, actor=self.owner, is_active=False)
        with self.assertRaises(ValidationError):
            self.add()
        update_service_catalog_entry(entry_id=self.entry.pk, actor=self.owner, is_active=True)
        hour_order = self.create_work_order(number="OS-HORA")
        with self.assertRaises(ValidationError):
            add_work_order_service_line(work_order_id=hour_order.pk, actor=self.owner, catalog_entry=self.entry,
                                        complexity=ServiceComplexity.MEDIUM, quantity=Decimal("1"))

    def test_balance_validation_still_applies(self):
        with self.assertRaises(ValidationError):
            self.add(quantity=Decimal("100000"))  # passaria do saldo do item
        self.assertFalse(WorkOrderServiceLine.objects.exists())


class CicloDoServicoTests(CatalogoBase):
    def test_full_cycle_and_rejection(self):
        line = self.add()
        d = self.today - timedelta(days=2)
        register_service_line_delivery(line_id=line.pk, actor=self.owner, delivered_at=d)
        reject_service_line(line_id=line.pk, actor=self.owner, rejected_at=d, reason="Ajustar layout fictício")
        line.refresh_from_db()
        self.assertEqual((line.delivery_status, line.rejection_count, line.delivered_at),
                         (ServiceLineStatus.IN_PROGRESS, 1, None))
        register_service_line_delivery(line_id=line.pk, actor=self.owner, delivered_at=d)
        accept_service_line(line_id=line.pk, actor=self.owner, accepted_at=self.today)
        with self.assertRaises(ValidationError):  # em andamento só se altera antes da entrega
            remove_work_order_service_line(line_id=line.pk, actor=self.owner)
        done = homologate_accepted_service_lines(work_order_id=self.wo.pk, actor=self.owner,
                                                 homologated_at=self.today, reference="Termo fictício 1/2026")
        self.assertEqual(len(done), 1)
        line.refresh_from_db()
        self.assertEqual(line.delivery_status, ServiceLineStatus.HOMOLOGATED)
        self.assertEqual(line.homologation_reference, "Termo fictício 1/2026")

    def test_dates_and_required_fields(self):
        line = self.add()
        with self.assertRaises(ValidationError):
            register_service_line_delivery(line_id=line.pk, actor=self.owner, delivered_at=self.today + timedelta(days=1))
        with self.assertRaises(ValidationError):
            register_service_line_delivery(line_id=line.pk, actor=self.owner, delivered_at=self.wo.opening_date - timedelta(days=1))
        register_service_line_delivery(line_id=line.pk, actor=self.owner, delivered_at=self.today)
        with self.assertRaises(ValidationError):
            reject_service_line(line_id=line.pk, actor=self.owner, rejected_at=self.today, reason="  ")
        with self.assertRaises(ValidationError):
            accept_service_line(line_id=line.pk, actor=self.owner, accepted_at=self.today - timedelta(days=1))


class TelasTests(CatalogoBase):
    def test_screens(self):
        self.client.force_login(self.owner)
        catalog = self.client.get(reverse("contracts:service_catalog", args=[self.contract.pk]))
        self.assertContains(catalog, "Desenvolvimento de funcionalidade fictícia")
        self.assertContains(catalog, "N/A")
        response = self.client.post(reverse("contracts:work_order_service_create", args=[self.contract.pk, self.wo.pk]),
                                    {"catalog_entry": self.entry.pk, "complexity": "MEDIA", "quantity": "4"})
        self.assertEqual(response.status_code, 302)
        line = WorkOrderServiceLine.objects.get()
        detail = self.client.get(reverse("contracts:work_order_detail", args=[self.contract.pk, self.wo.pk]))
        self.assertContains(detail, "Serviços do catálogo — memória de cálculo")
        self.assertContains(detail, "Registrar entrega")
        action = reverse("contracts:work_order_service_action", args=[self.contract.pk, self.wo.pk, line.pk, "entregar"])
        self.assertEqual(self.client.post(action, {"event_date": self.today.isoformat()}).status_code, 302)
        line.refresh_from_db()
        self.assertEqual(line.delivery_status, ServiceLineStatus.DELIVERED)
        # outra pessoa não acessa as telas de alteração
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse("contracts:service_catalog_create", args=[self.contract.pk])).status_code, 404)
