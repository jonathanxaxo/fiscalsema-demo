from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower


def normalized_label(value):
    return " ".join(value.split())


class Organization(models.Model):
    name = models.CharField("nome", max_length=200)
    is_active = models.BooleanField("ativa", default=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_organizations",
        verbose_name="criada por",
    )

    class Meta:
        ordering = ("name", "pk")
        verbose_name = "organização"
        verbose_name_plural = "organizações"
        constraints = [
            models.UniqueConstraint(Lower("name"), name="organizations_name_ci_unique")
        ]
        permissions = [("manage_organizations", "Pode administrar organizações e setores")]

    def clean(self):
        super().clean()
        self.name = normalized_label(self.name)
        if not self.name:
            raise ValidationError({"name": "Informe o nome da organização."})

    def save(self, *args, **kwargs):
        self.name = normalized_label(self.name)
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Sector(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="sectors",
        verbose_name="organização",
    )
    name = models.CharField("nome", max_length=200)
    is_active = models.BooleanField("ativo", default=True)
    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizado em", auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sectors",
        verbose_name="criado por",
    )

    class Meta:
        ordering = ("organization__name", "name", "pk")
        verbose_name = "setor"
        verbose_name_plural = "setores"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                models.F("organization"),
                name="organizations_sector_name_org_ci_unique",
            )
        ]

    def clean(self):
        super().clean()
        self.name = normalized_label(self.name)
        if not self.name:
            raise ValidationError({"name": "Informe o nome do setor."})
        if self.is_active and self.organization_id and not self.organization.is_active:
            raise ValidationError({"organization": "Um setor ativo exige organização ativa."})

    def save(self, *args, **kwargs):
        self.name = normalized_label(self.name)
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organization.name} — {self.name}"


class OrganizationEvent(models.Model):
    class EventType(models.TextChoices):
        ORGANIZATION_CREATED = "ORGANIZACAO_CRIADA", "Organização criada"
        ORGANIZATION_UPDATED = "ORGANIZACAO_ATUALIZADA", "Organização atualizada"
        ORGANIZATION_DEACTIVATED = "ORGANIZACAO_INATIVADA", "Organização inativada"
        ORGANIZATION_ACTIVATED = "ORGANIZACAO_ATIVADA", "Organização ativada"
        SECTOR_CREATED = "SETOR_CRIADO", "Setor criado"
        SECTOR_UPDATED = "SETOR_ATUALIZADO", "Setor atualizado"
        SECTOR_DEACTIVATED = "SETOR_INATIVADO", "Setor inativado"
        SECTOR_ACTIVATED = "SETOR_ATIVADO", "Setor ativado"
        USER_ASSIGNED = "USUARIO_VINCULADO", "Usuário vinculado"

    event_type = models.CharField("evento", max_length=30, choices=EventType.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="organization_events_performed",
        verbose_name="autor",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="events",
        verbose_name="organização",
    )
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="events",
        verbose_name="setor",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_assignment_events",
        verbose_name="usuário vinculado",
    )
    created_at = models.DateTimeField("registrado em", auto_now_add=True, db_index=True)
    details = models.JSONField("detalhes", default=dict, blank=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "evento de organização"
        verbose_name_plural = "eventos de organizações"

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.created_at:%d/%m/%Y %H:%M}"
