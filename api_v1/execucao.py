"""Execução autorizada de propostas do MCP com código de uso único (Sprint 30).

Fluxo:
1. A IA propõe (rascunho PENDENTE, válido por ``MCP_PROPOSAL_HOURS``).
2. A pessoa, logada no FiscalSema, confere o antes/depois e gera um código.
   O código aparece só para ela, vale ``MCP_CODE_MINUTES`` e é guardado
   apenas como HMAC.
3. A pessoa digita o código no chat; a IA chama ``executar_proposta``.
4. O sistema confere dono, cliente de IA, validade, código e tentativas,
   consome o código e grava pelos serviços oficiais (``confirm_assistant_draft``
   revalida permissão, regras e se o registro mudou).

Um "sim" no chat nunca executa. Pagamentos nunca são executados pela IA.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from .drafts import confirm_assistant_draft
from .models import AssistantDraft, AssistantDraftEvent

ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sem 0/O, 1/I/L
CODE_LENGTH = 8
BLOCKED_TYPES = {AssistantDraft.EntityType.PAYMENT}


class ExecutionRefused(Exception):
    """Recusa com mensagem segura (para a IA e para a tela)."""


def normalize_code(code):
    return "".join(ch for ch in str(code or "").upper() if ch in ALPHABET)


def _code_hash(draft_id, code):
    return salted_hmac("fiscalsema.mcp.codigo", f"{draft_id}:{normalize_code(code)}").hexdigest()


def can_issue_code(draft):
    return (
        draft.status == AssistantDraft.Status.PENDING
        and draft.created_by_application_id is not None
        and draft.entity_type not in BLOCKED_TYPES
        and not (draft.expires_at and draft.expires_at <= timezone.now())
    )


def issue_confirmation_code(*, draft_id, actor):
    """Gera um código novo (invalida o anterior) e devolve ``(código formatado, validade)``."""
    with transaction.atomic():
        draft = AssistantDraft.objects.select_for_update().filter(pk=draft_id, requested_by=actor).first()
        if draft is None:
            raise PermissionDenied("Rascunho não encontrado.")
        if draft.entity_type in BLOCKED_TYPES:
            raise ExecutionRefused("Pagamentos nunca são executados pela IA. Confirme nesta tela.")
        if not can_issue_code(draft):
            raise ExecutionRefused("Este rascunho não aceita código: já revisado, vencido ou não veio do MCP.")
        code = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))
        expires = timezone.now() + timedelta(minutes=settings.MCP_CODE_MINUTES)
        draft.confirmation_code_hash = _code_hash(draft.pk, code)
        draft.confirmation_code_expires_at = expires
        draft.confirmation_code_attempts = 0
        draft.save(update_fields=(
            "confirmation_code_hash", "confirmation_code_expires_at", "confirmation_code_attempts",
        ))
        AssistantDraftEvent.objects.create(
            event_type=AssistantDraftEvent.EventType.CODE_ISSUED, draft=draft,
            contract=draft.contract, actor=actor,
            details={"valido_ate": expires.isoformat(), "minutos": settings.MCP_CODE_MINUTES},
        )
    return f"{code[:4]}-{code[4:]}", expires


def _refuse(draft, actor, reason, *, detail):
    AssistantDraftEvent.objects.create(
        event_type=AssistantDraftEvent.EventType.CODE_REFUSED, draft=draft,
        contract=draft.contract, actor=actor, details={"motivo": detail},
    )
    return reason


def _check_and_consume(*, draft_id, code, actor, application):
    """Confere tudo e consome o código.

    Devolve ``(draft, recusa)``: ``recusa`` é a mensagem de recusa, ``""`` quando
    pode executar, ou ``None`` quando a proposta já tinha sido executada.
    """
    with transaction.atomic():
        draft = AssistantDraft.objects.select_for_update().filter(pk=draft_id, requested_by=actor).first()
        if draft is None:
            raise ExecutionRefused("Proposta não encontrada.")
        if draft.created_by_application_id != application.pk:
            return draft, _refuse(draft, actor, "Esta proposta foi feita por outro cliente de IA.",
                                  detail="outro_cliente")
        if draft.status == AssistantDraft.Status.CONFIRMED:
            return draft, None  # repetição: já executada, nada a fazer
        if draft.status != AssistantDraft.Status.PENDING:
            return draft, "Esta proposta foi rejeitada e não pode ser executada."
        if draft.entity_type in BLOCKED_TYPES:
            return draft, _refuse(draft, actor, "Pagamentos nunca são executados pela IA.",
                                  detail="pagamento_bloqueado")
        now = timezone.now()
        if draft.expires_at and draft.expires_at <= now:
            return draft, _refuse(draft, actor, "Esta proposta venceu. Faça uma nova proposta.",
                                  detail="proposta_vencida")
        if not draft.confirmation_code_hash or not draft.confirmation_code_expires_at or (
            draft.confirmation_code_expires_at <= now
        ):
            return draft, _refuse(
                draft, actor,
                "Não há código válido. A pessoa deve abrir a proposta no FiscalSema e gerar um código.",
                detail="sem_codigo_valido",
            )
        if not constant_time_compare(draft.confirmation_code_hash, _code_hash(draft.pk, code)):
            draft.confirmation_code_attempts += 1
            fields = ["confirmation_code_attempts"]
            message = "Código incorreto."
            if draft.confirmation_code_attempts >= settings.MCP_CODE_MAX_ATTEMPTS:
                draft.confirmation_code_hash = ""
                fields.append("confirmation_code_hash")
                message = "Código incorreto. Limite de tentativas atingido: gere um novo código no FiscalSema."
            draft.save(update_fields=fields)
            return draft, _refuse(draft, actor, message, detail="codigo_incorreto")
        draft.confirmation_code_hash = ""  # uso único
        draft.save(update_fields=["confirmation_code_hash"])
        return draft, ""


def execute_with_code(*, draft_id, code, actor, application):
    """Executa a proposta. Devolve ``(draft, já_estava_executada)``; recusa com ``ExecutionRefused``."""
    draft, refusal = _check_and_consume(draft_id=draft_id, code=code, actor=actor, application=application)
    if refusal is None:
        return draft, True
    if refusal:
        raise ExecutionRefused(refusal)
    try:
        draft, _target = confirm_assistant_draft(draft_id=draft.pk, actor=actor, channel="mcp_codigo")
    except ValidationError as exc:
        raise ExecutionRefused(f"Execução recusada pela validação: {exc.messages[0]}") from exc
    except PermissionDenied as exc:
        raise ExecutionRefused(f"Execução recusada: {exc}") from exc
    return draft, False
