"""Cliente do provedor de IA (Sprint 21).

Lógica trazida do projeto de referência da IA da equipe e reescrita em Python,
somente com a biblioteca padrão:

- API no formato compatível com OpenAI (``/chat/completions`` e ``/models``).
  Hoje aponta para o Gemini; outro provedor compatível (ex.: OpenAI) é só
  configuração (``ASSISTANT_BASE_URL``, ``ASSISTANT_MODELS``, ``ASSISTANT_API_KEY``).
- Modelos de reserva: se um modelo responder 429/404/403/5xx ou não começar a
  responder no tempo, tenta o próximo. 401 (chave recusada) interrompe.
- Raciocínio mínimo: tenta ``reasoning_effort`` "minimal" → "low" → "none" →
  sem o parâmetro quando o modelo recusa com 400, e lembra o nível aceito.
- Tempo-limite só até o início da resposta; depois o texto pode demorar o
  quanto precisar (limite generoso entre partes, nunca corta o que já chegou).
- A chave nunca é registrada em log nem devolvida em mensagens.
"""

import http.client
import json
import logging
import re
import ssl
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from django.conf import settings

logger = logging.getLogger(__name__)

REASONING_LEVELS = ("minimal", "low", "none", None)  # None = não envia o parâmetro
RETRY_NEXT_MODEL = {403, 404, 408, 429, 500, 502, 503, 504}
MAX_MODELS = 6
STREAM_READ_TIMEOUT = 60  # segundos entre partes depois que a resposta começou

_reasoning_by_model = {}
_working_model = None
_discovered_models = None


class ProviderError(Exception):
    """Falha do provedor com mensagem já pronta para o usuário (sem segredos)."""

    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass
class ProviderStream:
    model: str
    ms_to_response: int
    chunks: object = field(repr=False)

    def __iter__(self):
        return iter(self.chunks)


def is_configured():
    return bool(settings.ASSISTANT_ENABLED and settings.ASSISTANT_API_KEY)


def friendly_message(status, detail=""):
    if status == 504:
        base = "O serviço de IA demorou demais para começar a responder."
    elif status == 429:
        base = "O limite de uso do serviço de IA foi atingido. Tente novamente em instantes."
    elif status in (401, 403):
        base = "A chave do serviço de IA foi recusada. Avise o administrador do sistema."
    elif status == 404:
        base = "Nenhum modelo de IA configurado está disponível."
    else:
        base = f"O serviço de IA respondeu com erro ({status})."
    return f"{base} Detalhe: {detail[:200]}" if detail else base


class _Response:
    """Resposta HTTP mínima, para permitir simular o provedor nos testes."""

    def __init__(self, conn, resp):
        self.conn, self.resp, self.status = conn, resp, resp.status

    def lines(self):
        if self.conn.sock is not None:
            self.conn.sock.settimeout(STREAM_READ_TIMEOUT)
        for raw in self.resp:
            yield raw.decode("utf-8", errors="replace")

    def read_text(self, limit=4000):
        return self.resp.read(limit).decode("utf-8", errors="replace")

    def close(self):
        self.conn.close()


def _open(method, path, body=None, *, timeout):
    """Abre a requisição e devolve quando chegam os cabeçalhos da resposta."""
    base = urlsplit(settings.ASSISTANT_BASE_URL.rstrip("/"))
    connection_class = (
        http.client.HTTPSConnection if base.scheme == "https" else http.client.HTTPConnection
    )
    kwargs = {"timeout": timeout}
    if base.scheme == "https":
        kwargs["context"] = ssl.create_default_context()
    conn = connection_class(base.netloc, **kwargs)
    headers = {
        "Authorization": f"Bearer {settings.ASSISTANT_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream" if body and body.get("stream") else "application/json",
    }
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    conn.request(method, base.path + path, body=payload, headers=headers)
    return _Response(conn, conn.getresponse())


def _error_detail(response):
    try:
        data = json.loads(response.read_text())
        data = data[0] if isinstance(data, list) else data
        return str((data or {}).get("error", {}).get("message", ""))
    except (ValueError, AttributeError, OSError):
        return ""
    finally:
        response.close()


def candidate_models():
    """Modelos configurados ou, sem configuração, os 'flash' da chave (lite primeiro)."""
    global _discovered_models
    if settings.ASSISTANT_MODELS:
        return list(settings.ASSISTANT_MODELS)
    if _discovered_models is not None:
        return list(_discovered_models)
    try:
        response = _open("GET", "/models", timeout=settings.ASSISTANT_TIMEOUT_SECONDS)
    except OSError as error:
        raise ProviderError(504, friendly_message(504)) from error
    if response.status != 200:
        detail = _error_detail(response)
        raise ProviderError(response.status, friendly_message(response.status, detail))
    data = json.loads(response.read_text(limit=2_000_000) or "{}")
    response.close()
    ids = [str(item.get("id", "")).removeprefix("models/") for item in data.get("data", [])]
    blocked = ("image", "tts", "audio", "live", "embedding", "native", "computer", "robotics")
    text = [m for m in ids if "flash" in m and not any(word in m for word in blocked)]

    def newest_first(items):
        return sorted(items, key=_natural_key, reverse=True)

    lite = newest_first(m for m in text if "lite" in m and "preview" not in m and "exp" not in m)
    stable = newest_first(
        m for m in text if not any(word in m for word in ("lite", "preview", "exp", "thinking"))
    )
    rest = newest_first(m for m in text if m not in lite and m not in stable)
    _discovered_models = lite + stable + rest
    if not _discovered_models:
        raise ProviderError(404, friendly_message(404))
    return list(_discovered_models)


def _natural_key(text):
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


def _call_model(model, messages):
    start = REASONING_LEVELS.index(_reasoning_by_model.get(model, "minimal"))
    response = None
    for level in REASONING_LEVELS[start:]:
        body = {"model": model, "messages": messages, "stream": True, "temperature": 0.4}
        if level:
            body["reasoning_effort"] = level
        if response is not None:
            response.close()
        try:
            response = _open(
                "POST", "/chat/completions", body, timeout=settings.ASSISTANT_TIMEOUT_SECONDS
            )
        except OSError:
            return None  # travou ou caiu: o laço de modelos tenta o próximo
        if response.status != 400:
            if response.status == 200:
                _reasoning_by_model[model] = level
            return response
    return response


def _parse_stream(response):
    try:
        for line in response.lines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            content = line[5:].strip()
            if content == "[DONE]":
                break
            try:
                piece = json.loads(content)["choices"][0]["delta"].get("content")
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                continue
            if piece:
                yield piece
    finally:
        response.close()


def stream_chat(messages):
    """Envia as mensagens e devolve um ``ProviderStream`` com o texto em partes."""
    global _working_model
    if not is_configured():
        raise ProviderError(503, "O assistente está desativado neste ambiente.")
    started = time.monotonic()
    models = candidate_models()
    if _working_model in models:
        models = [_working_model] + [m for m in models if m != _working_model]
    last_status, last_detail = 504, ""
    for model in models[:MAX_MODELS]:
        response = _call_model(model, messages)
        if response is not None and response.status == 200:
            _working_model = model
            elapsed = int((time.monotonic() - started) * 1000)
            logger.info("assistente: modelo=%s ms_ate_resposta=%s", model, elapsed)
            return ProviderStream(model=model, ms_to_response=elapsed, chunks=_parse_stream(response))
        if response is None:
            last_status, last_detail = 504, ""
        else:
            last_status, last_detail = response.status, _error_detail(response)
        logger.warning("assistente: modelo=%s status=%s", model, last_status)
        if model == _working_model:
            _working_model = None
        if last_status == 401 or last_status not in RETRY_NEXT_MODEL | {400}:
            break
    raise ProviderError(last_status, friendly_message(last_status, last_detail))


def reset_state():
    """Limpa memórias de modelo e nível (usado pelos testes)."""
    global _working_model, _discovered_models
    _working_model, _discovered_models = None, None
    _reasoning_by_model.clear()
