import logging

from django.http import JsonResponse

from .models import ApiAccessEvent
from .services import AuthenticationFailure, RateLimitExceeded, authenticate_token


logger = logging.getLogger("api_v1.security")


def error_response(code, message, status, *, headers=None):
    response = JsonResponse(
        {"error": {"code": code, "message": message}},
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    for key, value in (headers or {}).items():
        response[key] = value
    return response


def bearer_token(request):
    value = request.headers.get("Authorization", "")
    scheme, separator, token = value.partition(" ")
    if not separator or scheme.casefold() != "bearer" or not token.strip():
        return ""
    return token.strip()


def authenticate_request(request):
    try:
        return authenticate_token(bearer_token(request))
    except RateLimitExceeded as exc:
        ApiAccessEvent.objects.create(
            event_type=ApiAccessEvent.EventType.DENIED,
            credential=exc.credential,
            actor=exc.credential.authorized_user,
            endpoint=request.path,
            method=request.method,
            status_code=429,
            details={"motivo": "limite_de_requisicoes"},
        )
        return error_response(
            "rate_limit_exceeded", "Limite de requisições excedido.", 429,
            headers={"Retry-After": "60"},
        )
    except AuthenticationFailure as exc:
        if exc.credential:
            ApiAccessEvent.objects.create(
                event_type=ApiAccessEvent.EventType.DENIED,
                credential=exc.credential,
                actor=exc.credential.authorized_user,
                endpoint=request.path,
                method=request.method,
                status_code=401,
                details={"motivo": exc.code},
            )
        else:
            logger.warning("API authentication denied path=%s", request.path)
        return error_response(
            exc.code, exc.message, 401,
            headers={"WWW-Authenticate": 'Bearer realm="fiscalsema-api"'},
        )


def record_access(request, response):
    credential = getattr(request, "api_credential", None)
    if credential is None:
        return
    ApiAccessEvent.objects.create(
        event_type=(ApiAccessEvent.EventType.QUERY if response.status_code < 400
                    else ApiAccessEvent.EventType.DENIED),
        credential=credential,
        actor=request.api_actor,
        contract=getattr(request, "api_contract", None),
        endpoint=request.path,
        method=request.method,
        status_code=response.status_code,
        result_count=getattr(request, "api_result_count", 0),
        details={"codigo": getattr(request, "api_error_code", "")},
    )
