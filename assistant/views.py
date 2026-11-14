"""Telas e endpoint do Assistente Arise (Sprint 21).

- ``GET /assistente/``: chat com a lista de conversas do próprio usuário.
- ``POST /assistente/perguntar/``: envia a pergunta (sessão + CSRF) e devolve
  a resposta em partes (streaming de texto).
- ``GET /assistente/conversas/<id>/mensagens/``: mensagens (painel flutuante).
- ``POST /assistente/conversas/<id>/excluir/``: exclui a conversa do usuário.

Somente leitura em relação aos dados do sistema: só grava a própria conversa
e a auditoria de metadados.
"""

import time
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .conhecimento import suggestions_for
from .ferramentas import authorized_data
from .limites import limit_message, record
from .models import AssistantConversation, AssistantMessage
from .prompt import MAX_QUESTION_CHARS, PROFILE_LABELS, build_messages
from .provedor import ProviderError, is_configured, stream_chat

ROUTE = "assistant:chat"


def purge_expired():
    limit = timezone.now() - timedelta(days=settings.ASSISTANT_RETENTION_DAYS)
    AssistantConversation.objects.filter(updated_at__lt=limit).delete()


def _own_conversations(user):
    return AssistantConversation.objects.filter(user=user)


@require_GET
@login_required
def conversation_messages(request, pk):
    """Mensagens de uma conversa do próprio usuário (usado pelo painel flutuante)."""
    conversation = get_object_or_404(_own_conversations(request.user), pk=pk)
    return JsonResponse(
        {
            "id": conversation.pk,
            "titulo": conversation.title,
            "mensagens": list(conversation.messages.values("role", "content")),
        }
    )


@require_GET
@login_required
def chat(request, pk=None):
    purge_expired()
    current = get_object_or_404(_own_conversations(request.user), pk=pk) if pk else None
    return render(
        request,
        "assistant/chat.html",
        {
            "enabled": is_configured(),
            "conversations": _own_conversations(request.user)[:30],
            "current": current,
            "chat_messages": current.messages.all() if current else (),
            "suggestions": suggestions_for(request.user.profile),
            "profile_label": PROFILE_LABELS.get(request.user.profile, request.user.profile),
            "retention_days": settings.ASSISTANT_RETENTION_DAYS,
            "max_question": MAX_QUESTION_CHARS,
        },
    )


def _error(message, status):
    return JsonResponse({"erro": message}, status=status)


@require_POST
@login_required
def ask(request):
    user, profile = request.user, request.user.profile
    if not is_configured():
        return _error("O assistente está desativado neste ambiente.", 503)
    question = (request.POST.get("pergunta") or "").strip()
    if not question:
        return _error("Escreva uma pergunta.", 400)
    if len(question) > MAX_QUESTION_CHARS:
        return _error(f"A pergunta pode ter até {MAX_QUESTION_CHARS} caracteres.", 400)
    blocked = limit_message(user)
    if blocked:
        record(user, status_code=429, profile=profile, route=ROUTE)
        return _error(blocked, 429)

    conversation = None
    conversation_id = (request.POST.get("conversa") or "").strip()
    if conversation_id:
        if not conversation_id.isdigit():
            return _error("Conversa inválida.", 400)
        conversation = _own_conversations(user).filter(pk=int(conversation_id)).first()
        if conversation is None:
            return _error("Conversa não encontrada.", 404)
    history = list(conversation.messages.values("role", "content")) if conversation else []

    started = time.monotonic()
    try:
        stream = stream_chat(
            build_messages(
                question, profile=profile, route=ROUTE, history=history,
                data=authorized_data(user, route=ROUTE),
            )
        )
    except ProviderError as error:
        record(user, status_code=502, profile=profile, route=ROUTE, details={"status_provedor": error.status})
        return _error(error.message, 502)

    if conversation is None:
        conversation = AssistantConversation.objects.create(user=user, title=question[:80])
    AssistantMessage.objects.create(conversation=conversation, role=AssistantMessage.Role.USER, content=question)

    def generate():
        parts, completed = [], False
        try:
            for piece in stream:
                parts.append(piece)
                yield piece
            completed = True
        except Exception:  # queda do provedor no meio da resposta
            yield "\n\n_A resposta foi interrompida. Tente perguntar de novo._"
        finally:
            text = "".join(parts).strip()
            if text:
                AssistantMessage.objects.create(
                    conversation=conversation, role=AssistantMessage.Role.ASSISTANT, content=text
                )
            conversation.save(update_fields=["updated_at"])
            # A auditoria é imutável: um único registro, ao final, só com metadados.
            record(
                user, status_code=200, profile=profile, route=ROUTE,
                details={
                    "modelo": stream.model,
                    "ms_ate_resposta": stream.ms_to_response,
                    "ms_total": int((time.monotonic() - started) * 1000),
                    "concluida": completed,
                },
            )

    response = StreamingHttpResponse(generate(), content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store"
    response["X-Accel-Buffering"] = "no"
    response["X-Conversa-Id"] = str(conversation.pk)
    return response


@require_POST
@login_required
def delete(request, pk):
    get_object_or_404(_own_conversations(request.user), pk=pk).delete()
    messages.success(request, "Conversa excluída.")
    return redirect("assistant:chat")
