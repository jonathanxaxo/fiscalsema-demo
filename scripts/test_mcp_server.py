import unittest

from scripts.mcp_server import McpError, call_tool, handle_message


class FakeClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, *, query=None, body=None):
        self.calls.append((method, path, query, body))
        return {"data": [{"id": 1, "nome": "Contrato fictício"}]}


class McpServerTests(unittest.TestCase):
    def test_initialize_declares_tools_and_human_review(self):
        response = handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            client_factory=FakeClient,
        )
        self.assertEqual(response["result"]["serverInfo"]["name"], "fiscalsema-demo")
        self.assertIn("revisão humana", response["result"]["instructions"])

    def test_tools_list_does_not_expose_confirmation_or_direct_write(self):
        response = handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            client_factory=FakeClient,
        )
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("propor_rascunho", names)
        self.assertNotIn("confirmar_rascunho", names)
        self.assertNotIn("executar_acao", names)
        self.assertNotIn("acessar_banco", names)

    def test_query_is_read_only_and_scoped_to_api(self):
        client = FakeClient()
        result = call_tool(
            "consultar_resumo_contrato", {"contract_id": 7}, client,
        )
        self.assertFalse(result["executada"])
        self.assertTrue(result["somente_leitura"])
        self.assertEqual(client.calls[0][0:2], ("GET", "/api/v1/contracts/7/summary/"))

    def test_proposal_is_explicitly_not_executed(self):
        client = FakeClient()
        proposal = {
            "entity_type": "OS",
            "operation": "CRIAR",
            "context": {"contract_id": 7},
            "payload": {"number": "OS-DEMO-001"},
            "source_summary": "Fonte fictícia para demonstração.",
            "source_authority": "EXTRACAO_AUTOMATICA",
            "confidence_level": "PENDENTE",
            "evidence": [{"source": "Documento fictício", "reference": "DEMO-01"}],
        }
        result = call_tool("propor_rascunho", proposal, client)
        self.assertTrue(result["proposta_criada"])
        self.assertFalse(result["executada"])
        self.assertTrue(result["requer_aprovacao_humana"])
        self.assertEqual(client.calls[0][0:2], ("POST", "/api/v1/drafts/"))

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(McpError):
            call_tool("executar_pagamento", {}, FakeClient())

    def test_invalid_contract_id_is_rejected_before_api_call(self):
        client = FakeClient()
        with self.assertRaises(McpError):
            call_tool("consultar_itens", {"contract_id": 0}, client)
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
