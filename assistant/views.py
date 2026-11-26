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
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_GET, require_POST

from .anexos import MAX_REQUEST_BYTES, AttachmentError, InMemoryOnlyUploadHandler, read_attachment

from .conhecimento import suggestions_for
from .contexto_contrato import (
    InvalidContractContext,
    UnavailableContractContext,
    resolve_contract_context,
    resolve_request_contract,
)
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
    if conversation.contract_context_id is not None:
        try:
            resolve_contract_context(request.user, conversation.contract_context_id)
        except UnavailableContractContext as error:
            raise Http404(str(error)) from error
    return JsonResponse(
        {
            "id": conversation.pk,
            "titulo": conversation.title,
            "contrato_contexto": conversation.contract_context_id,
            "mensagens": list(conversation.messages.values("role", "content")),
        }
    )


@require_GET
@login_required
def chat(request, pk=None):
    purge_expired()
    current = get_object_or_404(_own_conversations(request.user), pk=pk) if pk else None
    try:
        contract_context = resolve_request_contract(request, strict=True)
    except (InvalidContractContext, UnavailableContractContext) as error:
        raise Http404(str(error)) from error
    if (
        current is not None
        and contract_context.requested
        and current.contract_context_id != contract_context.contract_id
    ):
        # A troca explícita de contrato começa com uma tela limpa. A conversa
        # anterior permanece preservada e vinculada somente ao contexto antigo.
        current = None
    if current is not None and not contract_context.requested:
        try:
            contract_context = resolve_contract_context(
                request.user,
                current.contract_context_id,
                requested=current.contract_context_id is not None,
            )
        except UnavailableContractContext as error:
            raise Http404(str(error)) from error
    return render(
        request,
        "assistant/chat.html",
        {
            "enabled": is_configured(),
            "conversations": _own_conversations(request.user)[:30],
            "current": current,
            "chat_messages": current.messages.all() if current else (),
            "suggestions": suggestions_for(
                request.user.profile, contract=contract_context.contract
            ),
            "profile_label": PROFILE_LABELS.get(request.user.profile, request.user.profile),
            "retention_days": settings.ASSISTANT_RETENTION_DAYS,
            "max_question": MAX_QUESTION_CHARS,
            **contract_context.template_values(),
        },
    )


def _error(message, status):
    return JsonResponse({"erro": message}, status=status)


@csrf_exempt  # o CSRF é conferido em ``_ask``, depois de trocar o leitor de upload
@require_POST
@login_required
def ask(request):
    """Sprint 32: o anexo (TR/contrato) fica só na memória — ler e descartar."""
    try:
        length = int(request.META.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    if length > MAX_REQUEST_BYTES:
        return _error("O arquivo passa de 4 MB. Envie um arquivo menor.", 413)
    request.upload_handlers = [InMemoryOnlyUploadHandler(request)]
    return _ask(request)


@csrf_protect
def _ask(request):
    user, profile = request.user, request.user.profile
    if not is_configured():
        return _error("O assistente está desativado neste ambiente.", 503)
    if getattr(request, "arise_upload_too_big", False):
        return _error("O arquivo passa de 4 MB. Envie um arquivo menor.", 413)
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
    raw_contract_id = (request.POST.get("contrato") or "").strip()
    try:
        contract_context = resolve_contract_context(
            user, raw_contract_id, requested=bool(raw_contract_id)
        )
    except InvalidContractContext:
        return _error("Contrato ativo inválido.", 400)
    except UnavailableContractContext:
        return _error(
            "O contrato ativo está indisponível ou fora do seu escopo autorizado.",
            404,
        )

    context_changed = False
    if (
        conversation is not None
        and conversation.contract_context_id != contract_context.contract_id
    ):
        conversation = None
        context_changed = True
    history = list(conversation.messages.values("role", "content")) if conversation else []

    attachment = None
    uploaded = request.FILES.get("anexo")
    if uploaded is not None:
        try:
            attachment = read_attachment(uploaded)
        except AttachmentError as error:
            record(user, status_code=400, profile=profile, route=ROUTE, details={"anexo": "recusado"})
            return _error(str(error), 400)
        finally:
            uploaded.close()  # descarta o arquivo; só o texto segue, e só nesta requisição
    audit_attachment = attachment.audit() if attachment else None

    started = time.monotonic()
    try:
        stream = stream_chat(
            build_messages(
                question, profile=profile, route=ROUTE, history=history,
                data=authorized_data(
                    user,
                    route=ROUTE,
                    contract_id=contract_context.contract_id,
                ),
                contract_context=contract_context.prompt_text,
                document=attachment,
            )
        )
    except ProviderError as error:
        record(user, status_code=502, profile=profile, route=ROUTE,
               details={"status_provedor": error.status, "anexo": audit_attachment})
        return _error(error.message, 502)
    stored_question = question
    if attachment is not None:
        stored_question = f"{question}\n\n📎 documento anexado: {attachment.name} (lido e descartado)"
    attachment = None  # o texto do documento não é guardado em lugar nenhum

    if conversation is None:
        conversation = AssistantConversation.objects.create(
            user=user,
            title=question[:80],
            contract_context=contract_context.contract,
        )
    AssistantMessage.objects.create(conversation=conversation, role=AssistantMessage.Role.USER, content=stored_question)

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
                    "anexo": audit_attachment,
                },
            )

    response = StreamingHttpResponse(generate(), content_type="text/plain; charset=utf-8")
    response["Cache-Control"] = "no-store"
    response["X-Accel-Buffering"] = "no"
    response["X-Conversa-Id"] = str(conversation.pk)
    if context_changed:
        response["X-Contexto-Alterado"] = "1"
    return response


@require_POST
@login_required
def delete(request, pk):
    get_object_or_404(_own_conversations(request.user), pk=pk).delete()
    messages.success(request, "Conversa excluída.")
    return redirect("assistant:chat")
