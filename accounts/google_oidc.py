"""Login com Google por OpenID Connect, sem dependência externa (Sprint 25).

Fluxo "código de autorização" com PKCE (S256), ``state`` e ``nonce``.
O ``id_token`` é recebido diretamente do endpoint de token do Google, por TLS
com verificação de certificado; nesse caso a especificação OpenID Connect
(Core 1.0, seção 3.1.3.7, item 6) permite usar a validação do servidor TLS no
lugar da checagem da assinatura. Mesmo assim são validados: emissor,
audiência, ``azp``, expiração, ``iat``, ``nonce``, ``sub`` e ``email_verified``.

Nenhum segredo é registrado em log ou devolvido em mensagens.
"""

import base64
import hashlib
import http.client
import json
import secrets
import ssl
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from django.conf import settings

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_HOST = "oauth2.googleapis.com"
TOKEN_PATH = "/token"
VALID_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
SESSION_KEY = "fiscalsema_google_oidc"
MAX_FLOW_SECONDS = 600
CLOCK_SKEW_SECONDS = 120


class GoogleLoginError(Exception):
    """Falha do login Google com mensagem segura para o usuário."""


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str
    hosted_domain: str


def is_configured():
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def start_flow(session, *, redirect_uri, intent, user_id=None):
    """Guarda state/nonce/verificador na sessão e devolve a URL do Google."""
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    session[SESSION_KEY] = {
        "state": state,
        "nonce": nonce,
        "verifier": verifier,
        "intent": intent,
        "user_id": user_id,
        "redirect_uri": redirect_uri,
        "started_at": int(time.time()),
    }
    query = {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "nonce": nonce,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTHORIZATION_ENDPOINT}?{urlencode(query)}"


def pop_flow(session, state):
    """Recupera e apaga o fluxo da sessão, conferindo o ``state`` e a validade."""
    flow = session.pop(SESSION_KEY, None)
    if not flow or not state or not secrets.compare_digest(str(flow.get("state", "")), str(state)):
        raise GoogleLoginError("A tentativa de login expirou ou é inválida. Tente novamente.")
    if int(time.time()) - int(flow.get("started_at", 0)) > MAX_FLOW_SECONDS:
        raise GoogleLoginError("A tentativa de login expirou. Tente novamente.")
    return flow


def exchange_code(code, *, verifier, redirect_uri):
    """Troca o código pelo token diretamente com o Google (TLS verificado)."""
    body = urlencode(
        {
            "code": code,
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
    )
    conn = http.client.HTTPSConnection(
        TOKEN_HOST, timeout=settings.GOOGLE_OAUTH_TIMEOUT_SECONDS,
        context=ssl.create_default_context(),
    )
    try:
        conn.request(
            "POST", TOKEN_PATH, body=body,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        )
        response = conn.getresponse()
        payload = response.read(200_000)
    except OSError as error:
        raise GoogleLoginError("Não foi possível falar com o Google agora. Tente novamente.") from error
    finally:
        conn.close()
    if response.status != 200:
        raise GoogleLoginError("O Google recusou o login. Tente novamente.")
    try:
        return json.loads(payload)
    except ValueError as error:
        raise GoogleLoginError("Resposta inválida do Google.") from error


def _decode_payload(id_token):
    parts = str(id_token or "").split(".")
    if len(parts) != 3:
        raise GoogleLoginError("Resposta inválida do Google.")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, TypeError) as error:
        raise GoogleLoginError("Resposta inválida do Google.") from error


def validate_id_token(id_token, *, nonce, now=None):
    """Valida as declarações do ``id_token`` e devolve a identidade Google."""
    claims = _decode_payload(id_token)
    now = now or time.time()
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if claims.get("iss") not in VALID_ISSUERS:
        raise GoogleLoginError("Login recusado: emissor inválido.")
    if client_id not in audiences:
        raise GoogleLoginError("Login recusado: o token não é deste aplicativo.")
    if len(audiences) > 1 and claims.get("azp") != client_id:
        raise GoogleLoginError("Login recusado: o token não é deste aplicativo.")
    if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] < now - CLOCK_SKEW_SECONDS:
        raise GoogleLoginError("Login expirado. Tente novamente.")
    if not isinstance(claims.get("iat"), (int, float)) or claims["iat"] > now + CLOCK_SKEW_SECONDS:
        raise GoogleLoginError("Login recusado: horário inválido.")
    if not nonce or not secrets.compare_digest(str(claims.get("nonce", "")), str(nonce)):
        raise GoogleLoginError("Login recusado: verificação de segurança falhou.")
    subject = str(claims.get("sub") or "")
    email = str(claims.get("email") or "").strip().casefold()
    if not subject or "@" not in email:
        raise GoogleLoginError("O Google não informou o e-mail da conta.")
    if claims.get("email_verified") not in (True, "true"):
        raise GoogleLoginError("O e-mail desta conta Google não está verificado.")
    return GoogleIdentity(
        subject=subject,
        email=email,
        name=str(claims.get("name") or "")[:200],
        hosted_domain=str(claims.get("hd") or "").casefold(),
    )


def complete_flow(session, *, state, code):
    """Confere o fluxo, troca o código e valida o token. Devolve (identidade, fluxo)."""
    flow = pop_flow(session, state)
    if not code:
        raise GoogleLoginError("O Google não concluiu o login.")
    tokens = exchange_code(code, verifier=flow["verifier"], redirect_uri=flow["redirect_uri"])
    identity = validate_id_token(tokens.get("id_token"), nonce=flow["nonce"])
    return identity, flow
