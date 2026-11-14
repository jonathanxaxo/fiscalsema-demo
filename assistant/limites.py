"""Limites de uso e auditoria do Assistente Arise (Sprint 21).

Reaproveita a tabela de eventos da API da Sprint 17 (``ApiAccessEvent``) com
o endpoint ``/assistente/``. Só metadados: nunca o texto da pergunta ou da
resposta.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from api_v1.models import ApiAccessEvent

ENDPOINT = "/assistente/"


def _events(user):
    return ApiAccessEvent.objects.filter(actor=user, endpoint=ENDPOINT)


def limit_message(user):
    """Mensagem de bloqueio quando o limite foi atingido; ``None`` se pode perguntar."""
    now = timezone.now()
    if _events(user).filter(created_at__gte=now - timedelta(minutes=1)).count() >= settings.ASSISTANT_PER_MINUTE:
        return "Muitas perguntas em 1 minuto. Aguarde um pouco e tente de novo."
    day_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
    if _events(user).filter(created_at__gte=day_start).count() >= settings.ASSISTANT_DAILY_LIMIT:
        return "Você atingiu o limite de perguntas de hoje. Volte amanhã."
    return None


def record(user, *, status_code, profile, route, details=None):
    """Registra metadados da pergunta (sem conteúdo)."""
    event_type = ApiAccessEvent.EventType.QUERY if status_code < 400 else ApiAccessEvent.EventType.DENIED
    safe = {"origem": "assistente_ia", "perfil": profile, "pagina": route[:60]}
    safe.update(details or {})
    return ApiAccessEvent.objects.create(
        event_type=event_type,
        actor=user,
        endpoint=ENDPOINT,
        method="POST",
        status_code=status_code,
        details=safe,
    )
