"""Sprint 71: contexto contratual seguro e isolado no Assistente Arise."""

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountStatus, UserProfile
from assistant import provedor
from assistant.models import AssistantConversation
from contracts.models import Contract, ContractItem, ContractItemUnit, WorkOrder
from contracts.tests import VALID_PASSWORD
from organizations.models import Organization


User = get_user_model()
ON = {
    "ASSISTANT_ENABLED": True,
    "ASSISTANT_API_KEY": "chave-ficticia",
    "ASSISTANT_MODELS": ["modelo-teste"],
    "ASSISTANT_PER_MINUTE": 20,
    "ASSISTANT_DAILY_LIMIT": 100,
}


def fake_stream(text="Resposta fictícia."):
    return provedor.ProviderStream(
        model="modelo-teste", ms_to_response=1, chunks=iter((text,))
    )


@override_settings(**ON)
class ContractContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = Organization.objects.create(name="Organização Contexto Arise")
        cls.fiscal = User.objects.create_user(
            email="fiscal.contexto@example.local",
            full_name="Fiscal Contexto",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=cls.organization,
        )
        cls.other_fiscal = User.objects.create_user(
            email="outro.contexto@example.local",
            full_name="Outro Fiscal",
            password=VALID_PASSWORD,
            profile=UserProfile.FISCAL_TITULAR,
            status=AccountStatus.ACTIVE,
            organization=cls.organization,
        )
        cls.contract_a = cls._contract(
            "DEMO-CTX-A/2026", Decimal("100000.00"), cls.fiscal
        )
        cls.contract_b = cls._contract(
            "DEMO-CTX-B/2026", Decimal("250000.00"), cls.fiscal
        )
        cls.unauthorized_contract = cls._contract(
            "DEMO-CTX-SEM-ACESSO/2026", Decimal("900000.00"), cls.other_fiscal
        )
        cls.archived_contract = cls._contract(
            "DEMO-CTX-ARQUIVADO/2026", Decimal("700000.00"), cls.fiscal
        )
        Contract.objects.filter(pk=cls.archived_contract.pk).update(
            archived_at=timezone.now(),
            archived_by=cls.fiscal,
            archive_reason="Arquivado para teste fictício.",
        )
        item = ContractItem.objects.create(
            contract=cls.contract_a,
            number="1",
            description="Serviço fictício do contexto",
            category="Serviço",
            unit=ContractItemUnit.HOUR,
            contracted_quantity=Decimal("100.0000"),
            unit_value=Decimal("100.00"),
            created_by=cls.fiscal,
        )
        cls.work_order = WorkOrder.objects.create(
            contract=cls.contract_a,
            item=item,
            number="OS-CTX-A/2026",
            description="OS exclusivamente fictícia",
            hours=Decimal("10.0000"),
            unit_value=item.unit_value,
            unit_name=item.unit_display,
            responsible="Responsável fictício",
            opening_date=date(2026, 1, 10),
            deadline=date(2026, 12, 10),
            process_number="PROC-OS-CTX-A",
            created_by=cls.fiscal,
        )

    @classmethod
    def _contract(cls, number, value, fiscal):
        return Contract.objects.create(
            number=number,
            process_number=f"PROC-{number}",
            object=f"Objeto fictício do {number}",
            contracting_organization=cls.organization,
            supplier_name="Fornecedor Fictício Ltda.",
            supplier_tax_id="12345678000199",
            signature_date=date(2026, 1, 1),
            validity_start=date(2026, 1, 1),
            validity_end=date(2027, 12, 31),
            original_value=value,
            responsible_fiscal=fiscal,
        )

    def setUp(self):
        self.client.force_login(self.fiscal)

    def ask(self, question, *, contract="", conversation=""):
        data = {"pergunta": question, "contrato": contract}
        if conversation:
            data["conversa"] = conversation
        with mock.patch("assistant.views.stream_chat", return_value=fake_stream()) as patched:
            response = self.client.post(reverse("assistant:ask"), data)
            body = (
                b"".join(response.streaming_content).decode()
                if response.streaming
                else ""
            )
        return response, body, patched

    def test_dashboard_query_exposes_backend_validated_active_contract(self):
        page = self.client.get(reverse("home"), {"contract": self.contract_b.pk})
        self.assertContains(page, f"Contrato ativo: {self.contract_b.number}")
        self.assertContains(page, f'name="contrato" value="{self.contract_b.pk}"')
        self.assertContains(page, self.contract_b.object)

    def test_default_dashboard_contract_is_used_even_without_query_string(self):
        page = self.client.get(reverse("home"))
        selected = min((self.contract_a, self.contract_b), key=lambda item: item.number)
        self.assertContains(page, f"Contrato ativo: {selected.number}")
        self.assertContains(page, f'name="contrato" value="{selected.pk}"')

    def test_contract_and_work_order_routes_keep_same_context(self):
        urls = (
            reverse("contracts:detail", args=[self.contract_a.pk]),
            reverse(
                "contracts:work_order_detail",
                args=[self.contract_a.pk, self.work_order.pk],
            ),
        )
        for url in urls:
            with self.subTest(url=url):
                page = self.client.get(url)
                self.assertContains(page, f"Contrato ativo: {self.contract_a.number}")
                self.assertContains(page, f'name="contrato" value="{self.contract_a.pk}"')

    def test_full_chat_receives_selected_contract(self):
        page = self.client.get(
            reverse("assistant:chat"), {"contract": self.contract_a.pk}
        )
        self.assertContains(page, f"Contrato ativo: {self.contract_a.number}")
        self.assertContains(page, f'name="contrato" value="{self.contract_a.pk}"')

    def test_selected_contract_limits_data_sent_to_model(self):
        response, _, patched = self.ask(
            "Qual é o valor deste contrato?", contract=str(self.contract_a.pk)
        )
        self.assertEqual(response.status_code, 200)
        system = patched.call_args.args[0][0]["content"]
        self.assertIn(self.contract_a.number, system)
        self.assertIn("R$ 100.000,00", system)
        self.assertNotIn(self.contract_b.number, system)
        self.assertNotIn("R$ 250.000,00", system)

    def test_switching_contract_creates_isolated_conversation(self):
        first, _, _ = self.ask("Saldo do primeiro?", contract=str(self.contract_a.pk))
        first_id = first["X-Conversa-Id"]
        second, _, patched = self.ask(
            "E agora, qual é o saldo?",
            contract=str(self.contract_b.pk),
            conversation=first_id,
        )
        second_id = second["X-Conversa-Id"]
        self.assertNotEqual(first_id, second_id)
        self.assertEqual(second["X-Contexto-Alterado"], "1")
        sent = patched.call_args.args[0]
        self.assertEqual([message["role"] for message in sent], ["system", "user"])
        self.assertIn(self.contract_b.number, sent[0]["content"])
        self.assertNotIn(self.contract_a.number, sent[0]["content"])
        self.assertEqual(AssistantConversation.objects.count(), 2)
        self.assertEqual(
            AssistantConversation.objects.get(pk=first_id).contract_context_id,
            self.contract_a.pk,
        )
        self.assertEqual(
            AssistantConversation.objects.get(pk=second_id).contract_context_id,
            self.contract_b.pk,
        )

    def test_same_contract_keeps_conversation_history(self):
        first, _, _ = self.ask("Primeira pergunta", contract=str(self.contract_b.pk))
        second, _, patched = self.ask(
            "Segunda pergunta",
            contract=str(self.contract_b.pk),
            conversation=first["X-Conversa-Id"],
        )
        self.assertEqual(first["X-Conversa-Id"], second["X-Conversa-Id"])
        self.assertNotIn("X-Contexto-Alterado", second)
        self.assertEqual(
            [message["role"] for message in patched.call_args.args[0]],
            ["system", "user", "assistant", "user"],
        )

    def test_invalid_contract_identifier_is_rejected_before_provider(self):
        response, _, patched = self.ask("Pergunta", contract="abc")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Contrato ativo inválido", response.json()["erro"])
        patched.assert_not_called()

    def test_unauthorized_or_archived_contract_is_rejected_before_provider(self):
        for contract in (self.unauthorized_contract, self.archived_contract):
            with self.subTest(contract=contract.number):
                response, _, patched = self.ask(
                    "Pergunta", contract=str(contract.pk)
                )
                self.assertEqual(response.status_code, 404)
                self.assertIn("indisponível", response.json()["erro"])
                patched.assert_not_called()

    def test_contract_without_orders_or_commitments_is_supported(self):
        response, _, patched = self.ask(
            "Existem OS ou empenhos?", contract=str(self.contract_b.pk)
        )
        self.assertEqual(response.status_code, 200)
        system = patched.call_args.args[0][0]["content"]
        self.assertIn(self.contract_b.number, system)
        self.assertIn('"ordens_servico_abertas":[]', system)
        self.assertIn('"empenhado":{"valor":"R$ 0,00"', system)

    def test_contracts_list_has_explicit_no_selection_state(self):
        page = self.client.get(reverse("contracts:list"))
        self.assertContains(page, "Nenhum contrato selecionado")
        self.assertContains(page, 'name="contrato" value=""')

    def test_opening_saved_conversation_restores_authorized_context(self):
        response, _, _ = self.ask("Pergunta", contract=str(self.contract_b.pk))
        page = self.client.get(
            reverse("assistant:conversation", args=[response["X-Conversa-Id"]])
        )
        self.assertContains(page, f"Contrato ativo: {self.contract_b.number}")
        self.assertContains(page, f'name="contrato" value="{self.contract_b.pk}"')

    def test_messages_endpoint_exposes_context_for_client_isolation(self):
        response, _, _ = self.ask("Pergunta", contract=str(self.contract_a.pk))
        payload = self.client.get(
            reverse("assistant:messages", args=[response["X-Conversa-Id"]])
        ).json()
        self.assertEqual(payload["contrato_contexto"], self.contract_a.pk)

    def test_explicit_context_change_does_not_render_old_messages(self):
        response, _, _ = self.ask("Mensagem do contrato A", contract=str(self.contract_a.pk))
        page = self.client.get(
            reverse("assistant:conversation", args=[response["X-Conversa-Id"]]),
            {"contract": self.contract_b.pk},
        )
        self.assertContains(page, f"Contrato ativo: {self.contract_b.number}")
        self.assertIsNone(page.context["current"])
        self.assertEqual(tuple(page.context["chat_messages"]), ())

    def test_other_profile_session_cannot_reuse_previous_conversation(self):
        response, _, _ = self.ask("Pergunta", contract=str(self.contract_a.pk))
        self.client.force_login(self.other_fiscal)
        denied, _, patched = self.ask(
            "Tentar reaproveitar contexto",
            contract=str(self.contract_a.pk),
            conversation=response["X-Conversa-Id"],
        )
        self.assertEqual(denied.status_code, 404)
        patched.assert_not_called()

    def test_revoked_contract_access_hides_saved_conversation(self):
        response, _, _ = self.ask("Dado do contrato", contract=str(self.contract_a.pk))
        conversation_id = response["X-Conversa-Id"]
        Contract.objects.filter(pk=self.contract_a.pk).update(
            responsible_fiscal=self.other_fiscal
        )
        full_page = self.client.get(
            reverse("assistant:conversation", args=[conversation_id])
        )
        messages = self.client.get(
            reverse("assistant:messages", args=[conversation_id])
        )
        self.assertEqual(full_page.status_code, 404)
        self.assertEqual(messages.status_code, 404)

    def test_context_markup_and_client_reset_contract_are_present(self):
        page = self.client.get(reverse("home"), {"contract": self.contract_a.pk})
        self.assertContains(page, "data-assistant-contract-context")
        self.assertContains(page, f'data-contract-context="{self.contract_a.pk}"')
        script = Path(settings.BASE_DIR, "assistant/static/assistant/chat.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("X-Contexto-Alterado", script)
        self.assertIn("contrato_contexto", script)
