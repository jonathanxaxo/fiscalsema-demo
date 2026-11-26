"""Sprint 75: autocadastro com órgão/setor e senha criada pelo link do e-mail.

A pessoa informa nome, e-mail, órgão e setor (escolhe na lista ou digita um
novo). A conta nasce como Fiscal Titular ativa, sem senha utilizável, com
acesso somente de leitura aos contratos fictícios da demonstração. A senha é
criada pelo link de uso único enviado ao e-mail: sem acesso à caixa de
entrada, ninguém usa a conta.
"""

import logging
from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from organizations.models import Organization, OrganizationEvent, Sector

from .models import AccountStatus, AuthenticationEvent, User, UserProfile
from .services import record_authentication_event, request_source_hash

logger = logging.getLogger(__name__)

# Marcas dos contratos fictícios da demonstração (comandos seed_demo_*).
DEMO_CONTRACT_MARKERS = ("[DEMO-APRESENTACAO]", "[DEMO-CARTEIRA]")


def _clean_name(value):
    return " ".join((value or "").split())


class SelfSignupForm(forms.Form):
    full_name = forms.CharField(label="Nome completo", max_length=200)
    email = forms.EmailField(label="E-mail", max_length=254)
    organization = forms.ModelChoiceField(
        label="Órgão",
        queryset=Organization.objects.none(),
        required=False,
        empty_label="Selecione o seu órgão",
    )
    new_organization = forms.CharField(
        label="Não encontrou? Digite o nome do órgão", max_length=200, required=False
    )
    sector = forms.ModelChoiceField(
        label="Setor",
        queryset=Sector.objects.none(),
        required=False,
        empty_label="Selecione o seu setor",
    )
    new_sector = forms.CharField(
        label="Não encontrou? Digite o nome do setor", max_length=200, required=False
    )
    # Campo invisível para pessoas; robôs costumam preenchê-lo.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = Organization.objects.filter(
            is_active=True
        ).order_by("name")
        self.fields["sector"].queryset = (
            Sector.objects.filter(is_active=True, organization__is_active=True)
            .select_related("organization")
            .order_by("organization__name", "name")
        )
        self.fields["sector"].label_from_instance = (
            lambda sector: f"{sector.organization.name} — {sector.name}"
        )
        self.resend_user = None

    def clean_full_name(self):
        return _clean_name(self.cleaned_data["full_name"])

    def clean_email(self):
        email = User.objects.normalize_login_email(self.cleaned_data["email"])
        existing = User.objects.filter(email__iexact=email).first()
        if existing is not None:
            if is_waiting_for_password(existing):
                self.resend_user = existing
            else:
                raise ValidationError(
                    "Já existe uma conta com este e-mail. Use “Esqueci minha senha” na tela de login."
                )
        return email

    def clean(self):
        data = super().clean()
        if data.get("website"):
            raise ValidationError("Não foi possível concluir o cadastro.")
        if self.resend_user is not None:
            return data
        organization = data.get("organization")
        new_organization = _clean_name(data.get("new_organization"))
        sector = data.get("sector")
        new_sector = _clean_name(data.get("new_sector"))
        if bool(organization) == bool(new_organization):
            self.add_error(
                "organization", "Escolha o seu órgão na lista ou digite o nome, apenas uma das opções."
            )
        if bool(sector) == bool(new_sector):
            self.add_error("sector", "Escolha o seu setor na lista ou digite o nome, apenas uma das opções.")
        if sector and new_organization:
            self.add_error("sector", "Para um órgão novo, digite também o nome do setor.")
        if sector and organization and sector.organization_id != organization.pk:
            self.add_error("sector", "O setor escolhido não pertence ao órgão escolhido.")
        data["new_organization"] = new_organization
        data["new_sector"] = new_sector
        return data


def is_waiting_for_password(user):
    """Conta de autocadastro que ainda não criou a senha pelo link."""
    return (
        not user.has_usable_password()
        and user.last_login is None
        and user.status == AccountStatus.ACTIVE
        and AuthenticationEvent.objects.filter(
            user=user,
            event_type=AuthenticationEvent.EventType.REGISTRATION_REQUESTED,
            details__autocadastro=True,
        ).exists()
    )


def signup_limit_reached(request):
    limit = settings.SELF_SIGNUP_LIMIT_PER_HOUR
    if limit <= 0:
        return False
    since = timezone.now() - timedelta(hours=1)
    return (
        AuthenticationEvent.objects.filter(
            event_type=AuthenticationEvent.EventType.REGISTRATION_REQUESTED,
            source_hash=request_source_hash(request),
            created_at__gte=since,
            details__autocadastro=True,
        ).count()
        >= limit
    )


def _organization_for(data):
    if data.get("organization"):
        return data["organization"], False
    name = data["new_organization"]
    existing = Organization.objects.filter(name__iexact=name).first()
    if existing is not None:
        if not existing.is_active:
            raise ValidationError("Este órgão não está disponível para novos cadastros.")
        return existing, False
    try:
        with transaction.atomic():
            return Organization.objects.create(name=name), True
    except IntegrityError:  # outra pessoa criou o mesmo órgão no mesmo instante
        return Organization.objects.get(name__iexact=name), False


def _sector_for(data, organization):
    if data.get("sector"):
        return data["sector"], False
    name = data["new_sector"]
    existing = Sector.objects.filter(organization=organization, name__iexact=name).first()
    if existing is not None:
        if not existing.is_active:
            raise ValidationError("Este setor não está disponível para novos cadastros.")
        return existing, False
    try:
        with transaction.atomic():
            return Sector.objects.create(organization=organization, name=name), True
    except IntegrityError:
        return Sector.objects.get(organization=organization, name__iexact=name), False


def demo_contracts():
    from contracts.models import Contract

    marked = Q()
    for marker in DEMO_CONTRACT_MARKERS:
        marked |= Q(notes__contains=marker)
    return Contract.objects.filter(archived_at__isnull=True).filter(marked).select_related(
        "responsible_fiscal"
    )


def grant_demo_read_only(user):
    """Acesso somente de leitura aos contratos fictícios, concedido pelo fiscal de cada um."""
    from contracts.models import (
        ContractAccess,
        ContractAccessStatus,
        ContractAccessType,
        ContractSharingEvent,
    )

    granted = 0
    for contract in demo_contracts():
        access, created = ContractAccess.objects.get_or_create(
            contract=contract,
            user=user,
            defaults={
                "access_type": ContractAccessType.READ_ONLY,
                "status": ContractAccessStatus.ACTIVE,
                "granted_by": contract.responsible_fiscal,
            },
        )
        if created:
            granted += 1
            ContractSharingEvent.objects.create(
                event_type=ContractSharingEvent.EventType.ACCESS_GRANTED,
                contract=contract,
                access=access,
                actor=None,
                details={"origem": "autocadastro", "usuario_id": user.pk, "tipo": "somente_leitura"},
            )
    return granted


@transaction.atomic
def create_self_signup(form, request):
    data = form.cleaned_data
    organization, organization_created = _organization_for(data)
    sector, sector_created = _sector_for(data, organization)
    user = User.objects.create_user(
        email=data["email"],
        password=None,
        full_name=data["full_name"],
        organization=organization,
        sector=sector,
        organization_name=organization.name,
        sector_name=sector.name,
        profile=UserProfile.FISCAL_TITULAR,
        status=AccountStatus.ACTIVE,
        must_change_password=False,
    )
    if organization_created:
        OrganizationEvent.objects.create(
            event_type=OrganizationEvent.EventType.ORGANIZATION_CREATED,
            actor=user,
            organization=organization,
            details={"origem": "autocadastro"},
        )
    if sector_created:
        OrganizationEvent.objects.create(
            event_type=OrganizationEvent.EventType.SECTOR_CREATED,
            actor=user,
            organization=organization,
            sector=sector,
            details={"origem": "autocadastro"},
        )
    granted = grant_demo_read_only(user)
    record_authentication_event(
        AuthenticationEvent.EventType.REGISTRATION_REQUESTED,
        request=request,
        user=user,
        email=user.email,
        details={
            "autocadastro": True,
            "perfil": user.profile,
            "orgao_criado": organization_created,
            "setor_criado": sector_created,
            "contratos_consulta": granted,
        },
    )
    return user


def send_create_password_email(user, request):
    """Envia o link de uso único para criar a senha. Nunca envia a senha."""
    context = {
        "user": user,
        "link": request.build_absolute_uri(
            reverse(
                "accounts:create_password",
                kwargs={
                    "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
                    "token": default_token_generator.make_token(user),
                },
            )
        ),
    }
    subject = render_to_string("accounts/criar_senha_assunto.txt", context).strip()
    body = render_to_string("accounts/criar_senha_email.txt", context)
    try:
        send_mail(subject, body, None, [user.email])
    except Exception:  # noqa: BLE001 — a conta fica criada; a pessoa pode pedir o reenvio
        logger.exception("Falha ao enviar o link de criação de senha (usuário %s).", user.pk)
        return False
    return True
