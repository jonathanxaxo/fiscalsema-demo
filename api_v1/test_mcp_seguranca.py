"""Testes de segurança de ponta a ponta do MCP/OAuth e compatibilidade (Sprint 31).

Simulam ataques comuns contra o servidor OAuth e o endpoint ``/mcp``.
Sem internet; dados exclusivamente fictícios.
"""

import json
from urllib.parse import parse_qs, urlparse

from django.test import Client
from oauth2_provider.models import AccessToken

from .mcp_remoto import TOOLS
from .test_mcp_remoto import REDIRECT, McpOAuthBase, pkce_pair

ALL_SCOPES = "fiscalsema.ler fiscalsema.propor fiscalsema.executar"


class AtaquesOAuthTests(McpOAuthBase):
    def authorize_code(self, *, scope="fiscalsema.ler", resource=None, user=None):
        client_id = self.register().json()["client_id"]
        verifier, challenge = pkce_pair()
        params = {"response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
                  "scope": scope, "state": "s", "code_challenge": challenge,
                  "code_challenge_method": "S256"}
        if resource:
            params["resource"] = resource
        self.client.force_login(user or self.owner)
        answer = self.client.post("/oauth/authorize/", {**params, "allow": "Autorizar"})
        self.client.logout()
        code = parse_qs(urlparse(answer["Location"]).query)["code"][0]
        return client_id, verifier, code

    def exchange(self, client_id, verifier, code, **extra):
        return self.client.post("/oauth/token/", {
            "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT,
            "client_id": client_id, "code_verifier": verifier, **extra,
        })

    def test_wrong_pkce_verifier_is_refused(self):
        client_id, _verifier, code = self.authorize_code()
        other_verifier, _ = pkce_pair()
        self.assertEqual(self.exchange(client_id, other_verifier, code).status_code, 400)

    def test_authorization_code_cannot_be_reused(self):
        client_id, verifier, code = self.authorize_code()
        self.assertEqual(self.exchange(client_id, verifier, code).status_code, 200)
        self.assertEqual(self.exchange(client_id, verifier, code).status_code, 400)

    def test_code_cannot_be_used_by_another_client(self):
        _client_id, verifier, code = self.authorize_code()
        intruder = self.register(client_name="Intruso").json()["client_id"]
        self.assertEqual(self.exchange(intruder, verifier, code).status_code, 400)

    def test_unregistered_redirect_uri_is_refused_without_redirecting(self):
        client_id = self.register().json()["client_id"]
        _verifier, challenge = pkce_pair()
        self.client.force_login(self.owner)
        response = self.client.get("/oauth/authorize/", {
            "response_type": "code", "client_id": client_id,
            "redirect_uri": "https://atacante.example/roubar", "scope": "fiscalsema.ler",
            "code_challenge": challenge, "code_challenge_method": "S256",
        })
        self.assertNotIn("atacante.example", response.get("Location", ""))
        self.assertContains(response, "Não foi possível autorizar", status_code=response.status_code)

    def test_unknown_scope_is_refused(self):
        client_id = self.register().json()["client_id"]
        _verifier, challenge = pkce_pair()
        self.client.force_login(self.owner)
        response = self.client.get("/oauth/authorize/", {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
            "scope": "fiscalsema.ler admin", "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        self.assertIn("error=invalid_scope", response.get("Location", ""))

    def test_refresh_cannot_escalate_scope(self):
        data = self.connect()
        response = self.client.post("/oauth/token/", {
            "grant_type": "refresh_token", "refresh_token": data["refresh_token"],
            "client_id": data["client_id"], "scope": ALL_SCOPES,
        })
        self.assertEqual(response.status_code, 400)

    def test_token_bound_to_other_resource_is_refused_at_mcp(self):
        client_id, verifier, code = self.authorize_code(resource="https://outro-servico.example/api")
        token = self.exchange(client_id, verifier, code,
                              resource="https://outro-servico.example/api").json()["access_token"]
        self.assertEqual(self.rpc("tools/list", token=token).status_code, 401)

    def test_token_in_query_string_is_refused(self):
        token = self.connect()["access_token"]
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        response = self.client.post(f"/mcp?access_token={token}", data=body,
                                    content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_revocation_endpoint_cuts_access(self):
        data = self.connect()
        response = self.client.post("/oauth/revoke_token/", {
            "token": data["access_token"], "client_id": data["client_id"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.rpc("tools/list", token=data["access_token"]).status_code, 401)

    def test_registration_management_requires_registration_token(self):
        response = self.register().json()
        path = f"/oauth/register/{response['client_id']}/"
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, HTTP_AUTHORIZATION="Bearer falso").status_code, 401)
        changed = self.client.put(
            path, data=json.dumps({"redirect_uris": ["http://inseguro.example/cb"],
                                   "token_endpoint_auth_method": "none"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {response['registration_access_token']}",
        )
        self.assertEqual(changed.status_code, 400)

    def test_consent_form_requires_csrf(self):
        client_id = self.register().json()["client_id"]
        _verifier, challenge = pkce_pair()
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(self.owner)
        response = browser.post("/oauth/authorize/", {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
            "scope": "fiscalsema.ler", "code_challenge": challenge,
            "code_challenge_method": "S256", "allow": "Autorizar",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AccessToken.objects.filter(user=self.owner).exists())

    def test_consent_page_cannot_be_framed(self):
        client_id = self.register().json()["client_id"]
        _verifier, challenge = pkce_pair()
        self.client.force_login(self.owner)
        response = self.client.get("/oauth/authorize/", {
            "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
            "scope": "fiscalsema.ler", "code_challenge": challenge, "code_challenge_method": "S256",
        })
        self.assertEqual(response["X-Frame-Options"], "DENY")


class CompatibilidadeMcpTests(McpOAuthBase):
    def test_unknown_protocol_version_falls_back_to_latest(self):
        token = self.connect()["access_token"]
        result = self.rpc("initialize", {"protocolVersion": "1999-01-01"}, token=token).json()["result"]
        self.assertEqual(result["protocolVersion"], "2025-11-25")
        self.assertEqual(result["capabilities"], {"tools": {"listChanged": False}})

    def test_older_supported_version_is_echoed(self):
        token = self.connect()["access_token"]
        result = self.rpc("initialize", {"protocolVersion": "2025-03-26"}, token=token).json()["result"]
        self.assertEqual(result["protocolVersion"], "2025-03-26")

    def test_batch_and_invalid_envelopes_are_rejected_cleanly(self):
        token = self.connect()["access_token"]
        for body in ("[]", '[{"jsonrpc":"2.0","id":1,"method":"ping"}]', '{"id":1,"method":"ping"}', '"texto"'):
            response = self.client.post("/mcp", data=body, content_type="application/json",
                                        HTTP_AUTHORIZATION=f"Bearer {token}")
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.json()["error"]["code"], -32600)

    def test_ping_options_and_no_store(self):
        token = self.connect()["access_token"]
        ping = self.rpc("ping", token=token)
        self.assertEqual(ping.json()["result"], {})
        self.assertEqual(ping["Cache-Control"], "private, no-store")
        self.assertEqual(self.client.options("/mcp").status_code, 204)

    def test_oversized_body_is_refused(self):
        token = self.connect()["access_token"]
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {"x": "a" * 250_000}})
        response = self.client.post("/mcp", data=body, content_type="application/json",
                                    HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 413)

    def test_tool_errors_do_not_leak_internals(self):
        token = self.connect(scope=ALL_SCOPES)["access_token"]
        for name, arguments in (
            ("consultar_itens", {"contract_id": "1; DROP TABLE"}),
            ("analisar_divergencias", {"entity_type": "X", "target_id": 1, "document_values": {"a": 1}}),
            ("executar_proposta", {"draft_id": 999999, "codigo": "ABCD-EFGH"}),
            ("nao_existe", {}),
        ):
            result = self.call(token, name, arguments)
            self.assertTrue(result["isError"], name)
            text = result["content"][0]["text"]
            self.assertNotIn("Traceback", text)
            self.assertNotIn("SELECT", text.upper())


class CatalogoDeFerramentasTests(McpOAuthBase):
    def test_catalog_has_no_generic_or_forbidden_tools(self):
        forbidden = ("sql", "query", "banco", "editar", "excluir", "apagar", "homolog",
                     "atest", "liquid", "pagar", "autorizar")
        for tool in TOOLS:
            for word in forbidden:
                self.assertNotIn(word, tool["name"], tool["name"])
            self.assertIn(tool["_scope"], ("fiscalsema.ler", "fiscalsema.propor", "fiscalsema.executar"))
        writes = {tool["name"] for tool in TOOLS if not tool["annotations"]["readOnlyHint"]}
        self.assertEqual(writes, {"propor_rascunho", "executar_proposta"})

    def test_every_scope_sees_exactly_its_tools(self):
        expectations = {
            "fiscalsema.ler": {t["name"] for t in TOOLS if t["_scope"] == "fiscalsema.ler"},
            "fiscalsema.ler fiscalsema.propor": {t["name"] for t in TOOLS if t["_scope"] != "fiscalsema.executar"},
            ALL_SCOPES: {t["name"] for t in TOOLS},
        }
        for scope, expected in expectations.items():
            token = self.connect(scope=scope)["access_token"]
            listed = {t["name"] for t in self.rpc("tools/list", token=token).json()["result"]["tools"]}
            self.assertEqual(listed, expected, scope)
            self.assertFalse(any(key.startswith("_") for t in self.rpc(
                "tools/list", token=token).json()["result"]["tools"] for key in t))
