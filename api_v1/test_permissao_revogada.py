"""Sprint 62: permissão revogada depois do código bloqueia a execução pelo MCP."""
import json
from datetime import timedelta

from django.utils import timezone

from accounts.services import change_user_status
from contracts.models import Contract

from .models import ApiAccessEvent, AssistantDraft
from .test_mcp_remoto import ALL_SCOPES, McpOAuthBase
from .tests import ControlledAssistantDraftTests


class PermissaoRevogadaTests(McpOAuthBase):
    def _proposta_com_codigo(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        result = self.call(token, "propor_rascunho", {
            "entity_type": "CONTRATO", "operation": "ATUALIZAR",
            "context": {"target_id": self.contract.pk},
            "payload": {"notes": "Observação proposta pela IA fictícia"},
            "source_summary": "Documento fictício REF-62.", "source_authority": "EXTRACAO_AUTOMATICA",
            "confidence_level": "ENCONTRADO_EM_FONTE", "evidence": [{"source": "Documento fictício"}],
        })
        self.assertNotIn("isError", result, result)
        draft_id = json.loads(result["content"][0]["text"])["data"]["id"]
        self.client.force_login(self.owner)
        page = self.client.post(f"/rascunhos-ia/{draft_id}/codigo/")
        self.client.logout()
        return token, draft_id, page.context["confirmation_code"]

    def _confere_recusa(self, token, draft_id, code):
        result = self.call(token, "executar_proposta", {"draft_id": draft_id, "codigo": code})
        self.assertTrue(result.get("isError"), result)
        # Nada foi gravado e a proposta continua pendente.
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.notes, "")
        self.assertEqual(AssistantDraft.objects.get(pk=draft_id).status, AssistantDraft.Status.PENDING)
        # A recusa fica auditada, sem expor o código.
        bruto = code.replace("-", "")
        eventos = AssistantDraft.objects.get(pk=draft_id).events.all()
        self.assertNotIn(bruto, json.dumps([e.details for e in eventos]))
        auditoria = ApiAccessEvent.objects.filter(endpoint="/mcp", details__ferramenta="executar_proposta")
        self.assertTrue(auditoria.exists())
        self.assertNotIn(bruto, json.dumps([a.details for a in auditoria]))
        self.assertNotIn(code, json.dumps([a.details for a in auditoria]))
        return result

    def test_contrato_transferido_depois_do_codigo_recusa_execucao(self):
        token, draft_id, code = self._proposta_com_codigo()
        # O contrato passa para outro Fiscal: quem gerou o código perde o acesso de escrita.
        Contract.objects.filter(pk=self.contract.pk).update(responsible_fiscal=self.other)
        self._confere_recusa(token, draft_id, code)

    def test_conta_desativada_depois_do_codigo_recusa_execucao(self):
        token, draft_id, code = self._proposta_com_codigo()
        # Mesmo caminho da tela do Administrador: Usuários > Inativar.
        change_user_status(user_id=self.owner.pk, actor=self.admin, action="deactivate")
        result = self.rpc("tools/call", {"name": "executar_proposta",
                                         "arguments": {"draft_id": draft_id, "codigo": code}}, token=token)
        # Conta inativa: o token deixa de valer ou a ferramenta recusa; nunca executa.
        if result.status_code == 200:
            body = result.json()
            self.assertTrue(body.get("error") or body["result"].get("isError"), body)
        else:
            self.assertIn(result.status_code, (401, 403))
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.notes, "")
        self.assertEqual(AssistantDraft.objects.get(pk=draft_id).status, AssistantDraft.Status.PENDING)


class MensagemDeRecusaTests(ControlledAssistantDraftTests):
    """Sprint 62: a recusa aparece como frase limpa, na cor de alerta."""

    def test_proposta_vencida_mostra_frase_limpa_em_alerta(self):
        response = self.create_draft()
        self.assertEqual(response.status_code, 201, response.content)
        draft = AssistantDraft.objects.get(pk=response.json()["data"]["id"])
        AssistantDraft.objects.filter(pk=draft.pk).update(expires_at=timezone.now() - timedelta(minutes=1))
        self.client.force_login(self.owner)
        page = self.client.post(f"/rascunhos-ia/{draft.pk}/confirmar/", follow=True)
        html = page.content.decode()
        self.assertIn("Confirmação recusada: Esta proposta venceu.", html)
        self.assertNotIn("[&#x27;", html)
        self.assertNotIn("['", html)
        self.assertIn('class="danger" role="alert"', html)
        self.assertEqual(AssistantDraft.objects.get(pk=draft.pk).status, AssistantDraft.Status.PENDING)
