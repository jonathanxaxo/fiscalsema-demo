"""Cliente do provedor de IA: reservas, níveis de raciocínio e streaming (Sprint 21).

Nenhum teste acessa a internet: ``provedor._open`` é substituído por um falso.
"""

import json
from unittest import mock

from django.test import SimpleTestCase, override_settings

from assistant import provedor

CONFIG = {
    "ASSISTANT_ENABLED": True,
    "ASSISTANT_API_KEY": "chave-ficticia-de-teste",
    "ASSISTANT_BASE_URL": "https://provedor.invalid/v1",
    "ASSISTANT_MODELS": ["modelo-a", "modelo-b", "modelo-c"],
    "ASSISTANT_TIMEOUT_SECONDS": 12,
}


class FakeResponse:
    def __init__(self, status, pieces=(), error=""):
        self.status, self.pieces, self.error, self.closed = status, pieces, error, False

    def lines(self):
        for piece in self.pieces:
            yield "data: " + json.dumps({"choices": [{"delta": {"content": piece}}]}) + "\n"
        yield "data: [DONE]\n"

    def read_text(self, limit=4000):
        if self.error:
            return json.dumps({"error": {"message": self.error}})
        return json.dumps({"data": [{"id": "models/x-flash"}, {"id": "models/x-flash-lite"},
                                    {"id": "models/x-flash-image"}, {"id": "models/x-pro"}]})

    def close(self):
        self.closed = True


class FakeProvider:
    """Responde conforme um roteiro: {(modelo, nível): status}."""

    def __init__(self, script, pieces=("Olá", ", tudo certo.")):
        self.script, self.pieces, self.calls = script, pieces, []

    def __call__(self, method, path, body=None, *, timeout):
        if path == "/models":
            return FakeResponse(200)
        key = (body["model"], body.get("reasoning_effort"))
        self.calls.append(key)
        outcome = self.script.get(key, self.script.get(body["model"], 200))
        if outcome == "timeout":
            raise TimeoutError("sem resposta")
        return FakeResponse(outcome, self.pieces, error="motivo do provedor")


@override_settings(**CONFIG)
class ProvedorTests(SimpleTestCase):
    def setUp(self):
        provedor.reset_state()

    def run_chat(self, fake):
        with mock.patch.object(provedor, "_open", fake):
            stream = provedor.stream_chat([{"role": "user", "content": "oi"}])
            return stream, "".join(stream)

    def test_streams_text_and_starts_with_minimal_reasoning(self):
        fake = FakeProvider({})
        stream, text = self.run_chat(fake)
        self.assertEqual(text, "Olá, tudo certo.")
        self.assertEqual(stream.model, "modelo-a")
        self.assertEqual(fake.calls, [("modelo-a", "minimal")])

    def test_400_steps_down_reasoning_and_remembers_level(self):
        fake = FakeProvider({("modelo-a", "minimal"): 400, ("modelo-a", "low"): 400})
        self.run_chat(fake)
        self.assertEqual(fake.calls, [("modelo-a", "minimal"), ("modelo-a", "low"), ("modelo-a", "none")])
        fake.calls.clear()
        self.run_chat(fake)
        self.assertEqual(fake.calls, [("modelo-a", "none")])

    def test_all_levels_refused_falls_back_to_no_parameter(self):
        fake = FakeProvider({("modelo-a", level): 400 for level in ("minimal", "low", "none")})
        self.run_chat(fake)
        self.assertEqual(fake.calls[-1], ("modelo-a", None))

    def test_429_404_5xx_and_timeout_try_next_model(self):
        for outcome in (429, 404, 403, 500, 503, "timeout"):
            with self.subTest(outcome=outcome):
                provedor.reset_state()
                fake = FakeProvider({"modelo-a": outcome})
                stream, _ = self.run_chat(fake)
                self.assertEqual(stream.model, "modelo-b")

    def test_working_model_is_tried_first_next_time(self):
        self.run_chat(FakeProvider({"modelo-a": 429}))
        fake = FakeProvider({})
        self.run_chat(fake)
        self.assertEqual(fake.calls[0][0], "modelo-b")

    def test_401_stops_without_trying_other_models(self):
        fake = FakeProvider({"modelo-a": 401})
        with mock.patch.object(provedor, "_open", fake):
            with self.assertRaises(provedor.ProviderError) as ctx:
                provedor.stream_chat([{"role": "user", "content": "oi"}])
        self.assertEqual(ctx.exception.status, 401)
        self.assertEqual(len(fake.calls), 1)
        self.assertIn("chave do serviço de IA foi recusada", ctx.exception.message)

    def test_all_models_failing_returns_friendly_portuguese_message(self):
        fake = FakeProvider({"modelo-a": 429, "modelo-b": 429, "modelo-c": 429})
        with mock.patch.object(provedor, "_open", fake):
            with self.assertRaises(provedor.ProviderError) as ctx:
                provedor.stream_chat([{"role": "user", "content": "oi"}])
        self.assertIn("limite de uso", ctx.exception.message)
        self.assertNotIn("chave-ficticia-de-teste", ctx.exception.message)

    def test_key_never_appears_in_logs(self):
        fake = FakeProvider({"modelo-a": 500})
        with self.assertLogs("assistant.provedor", level="INFO") as logs:
            self.run_chat(fake)
        self.assertNotIn("chave-ficticia-de-teste", "\n".join(logs.output))

    def test_text_already_streaming_is_not_cut(self):
        long_pieces = tuple(f"parte {i} " for i in range(200))
        _, text = self.run_chat(FakeProvider({}, pieces=long_pieces))
        self.assertEqual(text, "".join(long_pieces))

    @override_settings(ASSISTANT_MODELS=[])
    def test_discovers_flash_models_lite_first(self):
        with mock.patch.object(provedor, "_open", FakeProvider({})):
            self.assertEqual(provedor.candidate_models(), ["x-flash-lite", "x-flash"])

    @override_settings(ASSISTANT_ENABLED=False)
    def test_disabled_assistant_refuses(self):
        with self.assertRaises(provedor.ProviderError) as ctx:
            provedor.stream_chat([{"role": "user", "content": "oi"}])
        self.assertEqual(ctx.exception.status, 503)
