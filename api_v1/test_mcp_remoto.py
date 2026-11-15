"""MCP remoto por identidade com OAuth (Sprint 28).

Fluxo completo sem internet: registro dinâmico do cliente, login da pessoa,
consentimento, troca do código com PKCE e chamadas JSON-RPC em ``/mcp``.
Dados exclusivamente fictícios.
"""

import base64
import hashlib
import json
import secrets
from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

from django.test import override_settings
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, RefreshToken

from accounts.models import AccountStatus
from contracts.models import Contract

from .models import ApiAccessEvent, AssistantDraft
from .tests import ApiTestBase

REDIRECT = "https://cliente-ia.example/callback"


def pkce_pair():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


class McpOAuthBase(ApiTestBase):
    def register(self, **overrides):
        body = {"client_name": "Cliente IA Fictício", "redirect_uris": [REDIRECT],
                "grant_types": ["authorization_code", "refresh_token"],
                "token_endpoint_auth_method": "none", **overrides}
        return self.client.post("/oauth/register/", data=json.dumps(body), content_type="application/json")

    def connect(self, user=None, scope="fiscalsema.ler"):
        """Faz o fluxo OAuth inteiro e devolve o JSON do token."""
        client_id = self.register().json()["client_id"]
        verifier, challenge = pkce_pair()
        params = {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
            "scope": scope, "state": "estado-ficticio", "code_challenge": challenge,
            "code_challenge_method": "S256", "resource": "http://testserver/mcp",
        }
        self.client.force_login(user or self.owner)
        page = self.client.get("/oauth/authorize/", params)
        self.assertEqual(page.status_code, 200, page.content[:500])
        self.assertContains(page, "Autorizar")
        form = {**params, "allow": "Autorizar"}
        answer = self.client.post("/oauth/authorize/", form)
        self.assertEqual(answer.status_code, 302)
        query = parse_qs(urlparse(answer["Location"]).query)
        self.assertEqual(query["state"], ["estado-ficticio"])
        self.client.logout()
        token = self.client.post("/oauth/token/", {
            "grant_type": "authorization_code", "code": query["code"][0], "redirect_uri": REDIRECT,
            "client_id": client_id, "code_verifier": verifier, "resource": "http://testserver/mcp",
        })
        self.assertEqual(token.status_code, 200, token.content)
        data = token.json()
        data["client_id"] = client_id
        return data

    def rpc(self, method, params=None, *, token=None, request_id=1):
        body = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
        return self.client.post("/mcp", data=json.dumps(body), content_type="application/json",
                                HTTP_ACCEPT="application/json, text/event-stream", **headers)

    def call(self, token, name, arguments=None):
        response = self.rpc("tools/call", {"name": name, "arguments": arguments or {}}, token=token)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["result"]


class DescobertaTests(McpOAuthBase):
    def test_unauthenticated_mcp_points_to_resource_metadata(self):
        response = self.rpc("initialize")
        self.assertEqual(response.status_code, 401)
        challenge = response["WWW-Authenticate"]
        self.assertIn('resource_metadata="http://testserver/.well-known/oauth-protected-resource/mcp"', challenge)

    def test_metadata_documents(self):
        resource = self.client.get("/.well-known/oauth-protected-resource/mcp").json()
        self.assertEqual(resource["resource"], "http://testserver/mcp")
        self.assertEqual(resource["authorization_servers"], ["http://testserver"])
        self.assertEqual(resource["scopes_supported"], ["fiscalsema.executar", "fiscalsema.ler", "fiscalsema.propor"])
        server = self.client.get("/.well-known/oauth-authorization-server").json()
        self.assertEqual(server["authorization_endpoint"], "http://testserver/oauth/authorize/")
        self.assertEqual(server["token_endpoint"], "http://testserver/oauth/token/")
        self.assertEqual(server["registration_endpoint"], "http://testserver/oauth/register/")
        self.assertEqual(server["code_challenge_methods_supported"], ["S256"])
        self.assertNotIn("introspection_endpoint", server)
        self.assertNotIn("implicit", server["grant_types_supported"])
        self.assertNotIn("password", server["grant_types_supported"])

    def test_management_and_device_routes_are_not_published(self):
        for path in ("/oauth/applications/", "/oauth/authorized_tokens/", "/oauth/introspect/",
                     "/oauth/device/", "/o/applications/"):
            self.assertEqual(self.client.get(path).status_code, 404, path)


class RegistroDinamicoTests(McpOAuthBase):
    def test_public_client_with_https_redirect_is_registered(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.content)
        app = Application.objects.get(client_id=response.json()["client_id"])
        self.assertEqual(app.client_type, "public")
        self.assertIsNone(app.user)

    def test_unsafe_registrations_are_refused(self):
        self.assertEqual(self.register(redirect_uris=["http://cliente-ia.example/cb"]).status_code, 401)
        self.assertEqual(self.register(redirect_uris=[]).status_code, 401)
        self.assertEqual(self.register(grant_types=["client_credentials"]).status_code, 401)
        self.assertEqual(self.register(redirect_uris=["javascript:alert(1)"]).status_code, 401)
        self.assertFalse(Application.objects.exists())

    @override_settings(MCP_DCR_PER_HOUR=2)
    def test_registration_is_rate_limited(self):
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register().status_code, 201)
        self.assertEqual(self.register().status_code, 401)


class FluxoOAuthTests(McpOAuthBase):
    def test_authorize_requires_login(self):
        client_id = self.register().json()["client_id"]
        _verifier, challenge = pkce_pair()
        response = self.client.get("/oauth/authorize/", {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
            "scope": "fiscalsema.ler", "code_challenge": challenge, "code_challenge_method": "S256",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("/conta/entrar/", response["Location"])

    def test_pkce_is_mandatory(self):
        client_id = self.register().json()["client_id"]
        self.client.force_login(self.owner)
        response = self.client.get("/oauth/authorize/", {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
            "scope": "fiscalsema.ler",
        })
        self.assertNotEqual(response.status_code, 200)
        self.assertNotIn("code=", response.get("Location", ""))

    def test_cancel_issues_no_code(self):
        client_id = self.register().json()["client_id"]
        _verifier, challenge = pkce_pair()
        params = {"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
                  "scope": "fiscalsema.ler", "code_challenge": challenge, "code_challenge_method": "S256"}
        self.client.force_login(self.owner)
        response = self.client.post("/oauth/authorize/", params)
        self.assertIn("error=access_denied", response["Location"])
        self.assertFalse(AccessToken.objects.filter(user=self.owner).exists())

    def test_tokens_are_stored_hashed_and_authorization_is_audited(self):
        data = self.connect()
        self.assertEqual(data["scope"], "fiscalsema.ler")
        stored = AccessToken.objects.get(user=self.owner)
        self.assertNotEqual(stored.token, data["access_token"])
        self.assertTrue(ApiAccessEvent.objects.filter(
            actor=self.owner, event_type=ApiAccessEvent.EventType.CONNECTION_AUTHORIZED,
        ).exists())

    def test_refresh_token_rotates(self):
        data = self.connect()
        response = self.client.post("/oauth/token/", {
            "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
            "client_id": data["client_id"],
        })
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotEqual(response.json()["refresh_token"], data["refresh_token"])
        reuse = self.client.post("/oauth/token/", {
            "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
            "client_id": data["client_id"],
        })
        self.assertEqual(reuse.status_code, 400)


class FerramentasMcpTests(McpOAuthBase):
    def test_initialize_and_read_only_tool_list(self):
        token = self.connect()["access_token"]
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18"}, token=token).json()["result"]
        self.assertEqual(init["protocolVersion"], "2025-06-18")
        self.assertIn("Homologação", init["instructions"])
        notification = self.client.post(
            "/mcp", data=json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(notification.status_code, 202)
        names = {tool["name"] for tool in self.rpc("tools/list", token=token).json()["result"]["tools"]}
        self.assertIn("listar_contratos_autorizados", names)
        self.assertNotIn("propor_rascunho", names)
        self.assertFalse(any("sql" in name or "editar" in name for name in names))

    def test_user_sees_only_own_contracts_and_calls_are_audited(self):
        token = self.connect()["access_token"]
        result = self.call(token, "listar_contratos_autorizados")
        data = json.loads(result["content"][0]["text"])
        self.assertEqual([item["id"] for item in data["results"]], [self.contract.pk])
        summary = self.call(token, "consultar_resumo_contrato", {"contract_id": self.contract.pk})
        self.assertIn("Não constitui atesto", summary["content"][0]["text"])
        event = ApiAccessEvent.objects.filter(endpoint="/mcp", actor=self.owner).first()
        self.assertEqual(event.details["ferramenta"], "consultar_resumo_contrato")
        self.assertEqual(event.contract, self.contract)
        self.assertEqual(event.details["cliente"], "Cliente IA Fictício")

        other_token = self.connect(self.other)["access_token"]
        listed = json.loads(self.call(other_token, "listar_contratos_autorizados")["content"][0]["text"])
        self.assertEqual(listed["results"], [])
        denied = self.call(other_token, "consultar_pendencias", {"contract_id": self.contract.pk})
        self.assertTrue(denied["isError"])
        self.assertIn("sem permissão", denied["content"][0]["text"])

    def test_all_read_tools_answer(self):
        token = self.connect()["access_token"]
        for name in ("consultar_itens", "consultar_empenhos", "consultar_ordens_servico",
                     "consultar_notas_fiscais", "consultar_pendencias"):
            result = self.call(token, name, {"contract_id": self.contract.pk})
            self.assertNotIn("isError", result, name)

    def test_read_scope_cannot_propose(self):
        token = self.connect()["access_token"]
        result = self.call(token, "propor_rascunho", {"entity_type": "CONTRATO"})
        self.assertTrue(result["isError"])
        self.assertIn("fiscalsema.propor", result["content"][0]["text"])
        self.assertFalse(AssistantDraft.objects.exists())

    def test_propose_creates_only_pending_draft_linked_to_client(self):
        token = self.connect(scope="fiscalsema.ler fiscalsema.propor")["access_token"]
        names = {tool["name"] for tool in self.rpc("tools/list", token=token).json()["result"]["tools"]}
        self.assertIn("propor_rascunho", names)
        before = Contract.objects.count()
        result = self.call(token, "propor_rascunho", {
            "entity_type": "CONTRATO", "operation": "CRIAR", "context": {},
            "payload": {
                "number": "039/2026", "process_number": "PROCESSO-MCP", "object": "Serviço fictício",
                "supplier_name": "Fornecedor Fictício", "supplier_tax_id": "12345678000199",
                "signature_date": "2026-02-01", "validity_start": "2026-02-01",
                "validity_end": "2027-01-31", "original_value": "5000,00", "status": "ATIVO", "notes": "",
            },
            "source_summary": "Documento fictício REF-MCP.", "source_authority": "EXTRACAO_AUTOMATICA",
            "confidence_level": "ENCONTRADO_EM_FONTE", "evidence": [{"source": "Documento fictício"}],
        })
        self.assertNotIn("isError", result, result)
        draft = AssistantDraft.objects.get()
        self.assertEqual(draft.status, AssistantDraft.Status.PENDING)
        self.assertEqual(draft.requested_by, self.owner)
        self.assertIsNone(draft.created_by_credential)
        self.assertEqual(draft.created_by_application.name, "Cliente IA Fictício")
        self.assertEqual(Contract.objects.count(), before)

    def test_unknown_method_and_bad_json(self):
        token = self.connect()["access_token"]
        self.assertEqual(self.rpc("resources/list", token=token).json()["error"]["code"], -32601)
        bad = self.client.post("/mcp", data="{", content_type="application/json",
                               HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.client.get("/mcp", HTTP_AUTHORIZATION=f"Bearer {token}").status_code, 405)

    @override_settings(MCP_PER_MINUTE=2)
    def test_per_minute_limit(self):
        token = self.connect()["access_token"]
        self.call(token, "listar_contratos_autorizados")
        self.call(token, "listar_contratos_autorizados")
        blocked = self.call(token, "listar_contratos_autorizados")
        self.assertTrue(blocked["isError"])
        self.assertIn("Limite", blocked["content"][0]["text"])


class RevogacaoTests(McpOAuthBase):
    def test_inactive_user_loses_access(self):
        token = self.connect()["access_token"]
        self.owner.status = AccountStatus.BLOCKED
        self.owner.save()
        self.assertEqual(self.rpc("tools/list", token=token).status_code, 401)

    def test_expired_token_is_refused(self):
        token = self.connect()["access_token"]
        AccessToken.objects.filter(user=self.owner).update(expires=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.rpc("tools/list", token=token).status_code, 401)

    def test_my_account_lists_and_revokes_connection(self):
        data = self.connect()
        self.client.force_login(self.owner)
        page = self.client.get("/conta/minha-conta/")
        self.assertContains(page, "Cliente IA Fictício")
        self.assertContains(page, "http://testserver/mcp")
        app = Application.objects.get(client_id=data["client_id"])
        # outra pessoa não revoga a conexão alheia
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(f"/conta/conexoes/{app.pk}/revogar/").status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.post(f"/conta/conexoes/{app.pk}/revogar/")
        self.assertRedirects(response, "/conta/minha-conta/", fetch_redirect_response=False)
        self.assertFalse(AccessToken.objects.filter(user=self.owner).exists())
        self.assertFalse(RefreshToken.objects.filter(user=self.owner, revoked__isnull=True).exists())
        self.assertTrue(ApiAccessEvent.objects.filter(
            actor=self.owner, event_type=ApiAccessEvent.EventType.CONNECTION_REVOKED,
        ).exists())
        self.client.logout()
        self.assertEqual(self.rpc("tools/list", token=data["access_token"]).status_code, 401)
        refresh = self.client.post("/oauth/token/", {
            "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
            "client_id": data["client_id"],
        })
        self.assertEqual(refresh.status_code, 400)
        self.assertNotContains(self.client.get("/conta/minha-conta/"), "Cliente IA Fictício", status_code=302)


class AnaliseSprint29Tests(McpOAuthBase):
    """Consultas novas e análise de divergências (Sprint 29), sempre sem gravar."""

    def text(self, result):
        self.assertNotIn("isError", result, result)
        return json.loads(result["content"][0]["text"])

    def test_new_read_tools_are_listed_for_read_scope(self):
        token = self.connect()["access_token"]
        names = {tool["name"] for tool in self.rpc("tools/list", token=token).json()["result"]["tools"]}
        expected = {"consultar_rateios", "consultar_execucoes", "consultar_pagamentos",
                    "consultar_posicao_financeira", "listar_documentos", "conferir_nota_fiscal",
                    "analisar_divergencias", "consultar_meus_rascunhos"}
        self.assertTrue(expected <= names)
        tools = {tool["name"]: tool for tool in self.rpc("tools/list", token=token).json()["result"]["tools"]}
        self.assertTrue(all(tools[name]["annotations"]["readOnlyHint"] for name in expected))

    def test_new_contract_tools_answer_and_payments_carry_notice(self):
        token = self.connect()["access_token"]
        for name in ("consultar_rateios", "consultar_execucoes", "listar_documentos"):
            self.text(self.call(token, name, {"contract_id": self.contract.pk}))
        payments = self.text(self.call(token, "consultar_pagamentos", {"contract_id": self.contract.pk}))
        self.assertIn("Não constitui atesto", payments["decision_notice"])
        position = self.text(self.call(token, "consultar_posicao_financeira", {"contract_id": self.contract.pk}))
        self.assertEqual(position["contract_id"], self.contract.pk)
        missing = self.call(token, "conferir_nota_fiscal", {"invoice_id": 999999})
        self.assertTrue(missing["isError"])

    def test_divergence_analysis_compares_without_writing(self):
        token = self.connect()["access_token"]
        before = Contract.objects.get(pk=self.contract.pk)
        events_before = ApiAccessEvent.objects.filter(endpoint="/mcp").count()
        data = self.text(self.call(token, "analisar_divergencias", {
            "entity_type": "CONTRATO", "target_id": self.contract.pk,
            "document_values": {
                "number": "001/2099", "original_value": "R$ 100.000,00",
                "validity_end": "09/01/2028", "supplier_name": "",
            },
        }))
        rows = {row["field"]: row["classification"] for row in data["fields"]}
        self.assertEqual(rows["number"], "IGUAL")
        self.assertEqual(rows["original_value"], "IGUAL")
        self.assertEqual(rows["validity_end"], "DIFERENTE")
        self.assertEqual(rows["supplier_name"], "AUSENTE_NO_DOCUMENTO")
        self.assertEqual(data["critical_differences"], ["validity_end"])
        self.assertFalse(data["written"])
        after = Contract.objects.get(pk=self.contract.pk)
        self.assertEqual(after.validity_end, before.validity_end)
        self.assertFalse(AssistantDraft.objects.exists())
        event = ApiAccessEvent.objects.filter(endpoint="/mcp").first()
        self.assertEqual(ApiAccessEvent.objects.filter(endpoint="/mcp").count(), events_before + 1)
        self.assertEqual(event.details["ferramenta"], "analisar_divergencias")
        self.assertEqual(event.contract, self.contract)
        self.assertNotIn("document_values", json.dumps(event.details))

    def test_divergence_analysis_rejects_unknown_fields_and_other_people(self):
        token = self.connect()["access_token"]
        unknown = self.call(token, "analisar_divergencias", {
            "entity_type": "CONTRATO", "target_id": self.contract.pk,
            "document_values": {"senha": "x"},
        })
        self.assertTrue(unknown["isError"])
        self.assertIn("Campos desconhecidos", unknown["content"][0]["text"])
        empty = self.call(token, "analisar_divergencias", {
            "entity_type": "CONTRATO", "target_id": self.contract.pk, "document_values": {},
        })
        self.assertTrue(empty["isError"])
        other_token = self.connect(self.other)["access_token"]
        denied = self.call(other_token, "analisar_divergencias", {
            "entity_type": "CONTRATO", "target_id": self.contract.pk,
            "document_values": {"number": "001/2099"},
        })
        self.assertTrue(denied["isError"])
        self.assertIn("sem permissão", denied["content"][0]["text"])

    def test_my_drafts_shows_only_own_drafts(self):
        AssistantDraft.objects.create(
            entity_type="CONTRATO", payload={"number": "X"}, source_summary="Fictício",
            created_by_credential=self.credential, requested_by=self.other,
        )
        token = self.connect()["access_token"]
        data = self.text(self.call(token, "consultar_meus_rascunhos"))
        self.assertEqual(data["results"], [])
        mine = AssistantDraft.objects.create(
            entity_type="CONTRATO", payload={"number": "Y"}, source_summary="Fictício",
            created_by_credential=self.credential, requested_by=self.owner,
        )
        data = self.text(self.call(token, "consultar_meus_rascunhos", {"status": "PENDENTE"}))
        self.assertEqual([item["id"] for item in data["results"]], [mine.pk])
        bad = self.call(token, "consultar_meus_rascunhos", {"status": "APAGAR"})
        self.assertTrue(bad["isError"])


class NormalizacaoTests(McpOAuthBase):
    def test_normalize_brazilian_formats(self):
        from .analise import normalize

        self.assertEqual(normalize("R$ 1.234,50"), normalize("1234.5"))
        self.assertEqual(normalize("31/12/2026"), "2026-12-31")
        self.assertEqual(normalize("  Fornecedor   Fictício "), "fornecedor fictício")
        self.assertEqual(normalize(None), "")


ALL_SCOPES = "fiscalsema.ler fiscalsema.propor fiscalsema.executar"


class ExecucaoAutorizadaTests(McpOAuthBase):
    """Execução por código de uso único (Sprint 30)."""

    def contract_update(self, **extra):
        return {
            "entity_type": "CONTRATO", "operation": "ATUALIZAR",
            "context": {"target_id": self.contract.pk},
            "payload": {"notes": "Observação corrigida pela proposta fictícia"},
            "source_summary": "Documento fictício REF-EXEC.", "source_authority": "EXTRACAO_AUTOMATICA",
            "confidence_level": "ENCONTRADO_EM_FONTE", "evidence": [{"source": "Documento fictício"}],
            **extra,
        }

    def propose(self, token, **extra):
        result = self.call(token, "propor_rascunho", self.contract_update(**extra))
        self.assertNotIn("isError", result, result)
        return json.loads(result["content"][0]["text"])

    def issue_code(self, draft_id, user=None):
        self.client.force_login(user or self.owner)
        page = self.client.post(f"/rascunhos-ia/{draft_id}/codigo/")
        self.client.logout()
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page["Cache-Control"], "private, no-store")
        return page.context["confirmation_code"]

    def execute(self, token, draft_id, code):
        return self.call(token, "executar_proposta", {"draft_id": draft_id, "codigo": code})

    def test_full_flow_with_code_executes_once(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        proposal = self.propose(token)
        draft_id = proposal["data"]["id"]
        self.assertIn(f"/rascunhos-ia/{draft_id}/", proposal["review_url"])
        self.assertIn("nada foi gravado", proposal["next_action"])
        # "sim" sem código não executa
        refused = self.execute(token, draft_id, "SIMSIMSIM")
        self.assertTrue(refused["isError"])
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.notes, "")
        code = self.issue_code(draft_id)
        draft = AssistantDraft.objects.get(pk=draft_id)
        self.assertNotIn(code.replace("-", ""), draft.confirmation_code_hash)
        result = self.execute(token, draft_id, code.lower())
        self.assertNotIn("isError", result, result)
        data = json.loads(result["content"][0]["text"])
        self.assertEqual(data["result"], "executada", result)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.notes, "Observação corrigida pela proposta fictícia")
        draft.refresh_from_db()
        self.assertEqual(draft.status, AssistantDraft.Status.CONFIRMED)
        self.assertEqual(draft.reviewed_by, self.owner)
        event = draft.events.get(event_type="RASCUNHO_CONFIRMADO")
        self.assertEqual(event.details["canal"], "mcp_codigo")
        self.assertTrue(draft.events.filter(event_type="CODIGO_EMITIDO").exists())
        self.assertNotIn(code, json.dumps([e.details for e in draft.events.all()]))
        audit = ApiAccessEvent.objects.filter(endpoint="/mcp", details__ferramenta="executar_proposta",
                                              status_code=200).first()
        self.assertNotIn(code, json.dumps(audit.details))
        again = json.loads(self.execute(token, draft_id, code)["content"][0]["text"])
        self.assertEqual(again["result"], "ja_executada_antes")

    def test_wrong_code_attempts_are_limited(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        draft_id = self.propose(token)["data"]["id"]
        code = self.issue_code(draft_id)
        for _ in range(5):
            self.assertTrue(self.execute(token, draft_id, "AAAA-AAAA")["isError"])
        blocked = self.execute(token, draft_id, code)
        self.assertTrue(blocked["isError"])
        self.assertIn("gerar um código", blocked["content"][0]["text"])
        self.assertEqual(AssistantDraft.objects.get(pk=draft_id).status, AssistantDraft.Status.PENDING)
        self.assertEqual(AssistantDraft.objects.get(pk=draft_id).events.filter(
            event_type="CODIGO_RECUSADO").count(), 6)

    def test_expired_code_and_expired_proposal(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        draft_id = self.propose(token)["data"]["id"]
        code = self.issue_code(draft_id)
        AssistantDraft.objects.filter(pk=draft_id).update(
            confirmation_code_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertTrue(self.execute(token, draft_id, code)["isError"])
        code = self.issue_code(draft_id)
        AssistantDraft.objects.filter(pk=draft_id).update(expires_at=timezone.now() - timedelta(seconds=1))
        expired = self.execute(token, draft_id, code)
        self.assertIn("venceu", expired["content"][0]["text"])
        # a tela também respeita a validade
        self.client.force_login(self.owner)
        self.client.post(f"/rascunhos-ia/{draft_id}/confirmar/")
        self.assertEqual(AssistantDraft.objects.get(pk=draft_id).status, AssistantDraft.Status.PENDING)
        page = self.client.post(f"/rascunhos-ia/{draft_id}/codigo/")
        self.assertEqual(page.status_code, 302)

    def test_requires_execute_scope_and_same_client(self):
        propose_only = self.connect(scope="fiscalsema.ler fiscalsema.propor")["access_token"]
        names = {tool["name"] for tool in self.rpc("tools/list", token=propose_only).json()["result"]["tools"]}
        self.assertNotIn("executar_proposta", names)
        draft_id = self.propose(propose_only)["data"]["id"]
        code = self.issue_code(draft_id)
        no_scope = self.execute(propose_only, draft_id, code)
        self.assertIn("fiscalsema.executar", no_scope["content"][0]["text"])
        other_client = self.connect(scope=ALL_SCOPES)["access_token"]
        refused = self.execute(other_client, draft_id, code)
        self.assertIn("outro cliente", refused["content"][0]["text"])
        self.assertEqual(AssistantDraft.objects.get(pk=draft_id).status, AssistantDraft.Status.PENDING)

    def test_other_person_cannot_issue_code_or_execute(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        draft_id = self.propose(token)["data"]["id"]
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(f"/rascunhos-ia/{draft_id}/codigo/").status_code, 404)
        self.client.logout()
        other_token = self.connect(self.other, scope=ALL_SCOPES)["access_token"]
        result = self.execute(other_token, draft_id, "ABCD-EFGH")
        self.assertIn("não encontrada", result["content"][0]["text"])

    def test_changed_record_blocks_execution(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        draft_id = self.propose(token)["data"]["id"]
        code = self.issue_code(draft_id)
        Contract.objects.filter(pk=self.contract.pk).update(notes="Alterado por outra pessoa")
        result = self.execute(token, draft_id, code)
        self.assertIn("mudou", result["content"][0]["text"])
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.notes, "Alterado por outra pessoa")

    def test_payment_drafts_never_get_code(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        draft = AssistantDraft.objects.create(
            entity_type="PAGAMENTO", payload={"amount": "1"}, source_summary="Fictício",
            requested_by=self.owner,
            created_by_application=Application.objects.get(client_id=AccessToken.objects.filter(
                user=self.owner).latest("created").application.client_id),
        )
        self.client.force_login(self.owner)
        detail = self.client.get(f"/rascunhos-ia/{draft.pk}/")
        self.assertContains(detail, "nunca é executado pela IA")
        self.assertNotContains(detail, "Gerar código de confirmação")
        self.assertEqual(self.client.post(f"/rascunhos-ia/{draft.pk}/codigo/").status_code, 302)
        self.client.logout()
        result = self.execute(token, draft.pk, "ABCD-EFGH")
        self.assertIn("Pagamentos nunca", result["content"][0]["text"])

    def test_idempotency_key_returns_same_proposal(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        first = self.propose(token, idempotency_key="chave-ficticia-001")
        second = self.propose(token, idempotency_key="chave-ficticia-001")
        self.assertEqual(first["data"]["id"], second["data"]["id"])
        self.assertTrue(second["repeated"])
        self.assertEqual(AssistantDraft.objects.count(), 1)

    def test_api_v1_drafts_still_work_without_expiry(self):
        draft = AssistantDraft.objects.create(
            entity_type="CONTRATO", payload={"number": "Z"}, source_summary="Fictício",
            created_by_credential=self.credential, requested_by=self.owner,
        )
        self.client.force_login(self.owner)
        page = self.client.get(f"/rascunhos-ia/{draft.pk}/")
        self.assertNotContains(page, "Gerar código de confirmação")
        self.assertEqual(self.client.post(f"/rascunhos-ia/{draft.pk}/codigo/").status_code, 302)


class DadosNovosSprint40Tests(McpOAuthBase):
    """A IA externa recebe prazos, memória de cálculo e situação da NF (Sprint 40)."""

    def test_work_order_and_invoice_carry_new_fields(self):
        from contracts.models import Invoice, WorkOrder, WorkOrderStatus
        from contracts.services import create_contract_item, create_invoice, create_work_order
        from contracts.test_invoices import invoice_data
        from contracts.test_items import item_data
        from contracts.test_work_orders import work_order_data

        item = create_contract_item(contract_id=self.contract.pk, actor=self.owner, **item_data())
        wo = create_work_order(contract_id=self.contract.pk, actor=self.owner,
                               **work_order_data(item, status=WorkOrderStatus.IN_PROGRESS))
        nf = create_invoice(work_order_id=wo.pk, actor=self.owner,
                            **invoice_data(self.contract, gross_value=Decimal("100.00"),
                                           accepted_value=Decimal("100.00")))
        Invoice.objects.filter(pk=nf.pk).update(returned_at=nf.issue_date, return_reason="Valor errado")
        token = self.connect()["access_token"]
        orders = json.loads(self.call(token, "consultar_ordens_servico", {"contract_id": self.contract.pk})["content"][0]["text"])
        order = orders["results"][0]
        for key in ("factory_deadline", "spent_hours_informed", "deadline_situation", "service_lines"):
            self.assertIn(key, order)
        self.assertIn("label", order["deadline_situation"])
        invoices = json.loads(self.call(token, "consultar_notas_fiscais", {"contract_id": self.contract.pk})["content"][0]["text"])
        returned = invoices["results"][0]
        self.assertTrue(returned["is_returned"])
        self.assertFalse(returned["counts_in_calculations"])
        self.assertIsNone(returned["dimensioned_value"])
        init = self.rpc("initialize", {"protocolVersion": "2025-06-18"}, token=token).json()["result"]
        self.assertIn("is_returned=true", init["instructions"])
