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
        self.assertEqual(resource["scopes_supported"], ["fiscalsema.ler", "fiscalsema.propor"])
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
