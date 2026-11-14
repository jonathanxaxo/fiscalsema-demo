"""Conversas do Assistente IA (Sprint 21).

Cada conversa pertence a um único usuário e só ele a vê. Conversas ficam
guardadas por ``ASSISTANT_RETENTION_DAYS`` dias e podem ser excluídas pelo
próprio usuário. Nenhum dado de contrato é gravado aqui.
"""

from django.conf import settings
from django.db import models


class AssistantConversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistant_conversations",
        verbose_name="usuário",
    )
    title = models.CharField("título", max_length=120)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True, db_index=True)

    class Meta:
        ordering = ("-updated_at", "-pk")
        verbose_name = "conversa do assistente"
        verbose_name_plural = "conversas do assistente"

    def __str__(self):
        return self.title


class AssistantMessage(models.Model):
    class Role(models.TextChoices):
        USER = "user", "Usuário"
        ASSISTANT = "assistant", "Assistente"

    conversation = models.ForeignKey(
        AssistantConversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="conversa",
    )
    role = models.CharField("papel", max_length=10, choices=Role.choices)
    content = models.TextField("conteúdo")
    created_at = models.DateTimeField("criada em", auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        verbose_name = "mensagem do assistente"
        verbose_name_plural = "mensagens do assistente"
