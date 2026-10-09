from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    SetPasswordForm,
    UserChangeForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from organizations.models import Organization, Sector

from .models import AccountStatus, RegistrationRequest, User, UserProfile
from .services import (
    is_login_blocked,
    record_authentication_event,
    record_login_failure,
)


PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 24


class NormalizedRegistrationEmailField(forms.EmailField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label", "E-mail")
        kwargs.setdefault("max_length", 254)
        kwargs.setdefault(
            "help_text",
            "Informe um endereço individual válido. O e-mail será usado para entrar no sistema.",
        )
        error_messages = {
            "required": "Informe o e-mail.",
            "invalid": "Informe um e-mail válido, como nome@dominio.gov.br.",
        }
        error_messages.update(kwargs.pop("error_messages", {}))
        kwargs["error_messages"] = error_messages
        kwargs.setdefault("widget", forms.EmailInput(attrs={"autocomplete": "email"}))
        super().__init__(*args, **kwargs)

    def clean(self, value):
        return User.objects.normalize_login_email(super().clean(value))


def apply_password_input_limits(form, field_names):
    for field_name in field_names:
        field = form.fields[field_name]
        field.widget.attrs["minlength"] = PASSWORD_MIN_LENGTH
        field.widget.attrs["maxlength"] = PASSWORD_MAX_LENGTH


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="E-mail",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    error_messages = {
        "invalid_login": "E-mail ou senha inválidos.",
        "inactive": "E-mail ou senha inválidos.",
    }

    def __init__(self, request=None, *args, **kwargs):
        data = kwargs.get("data")
        if data:
            normalized_data = data.copy()
            normalized_data["username"] = User.objects.normalize_login_email(
                data.get("username", "")
            )
            kwargs["data"] = normalized_data
        super().__init__(request=request, *args, **kwargs)

    def clean(self):
        email = User.objects.normalize_login_email(self.data.get("username", ""))
        if is_login_blocked(email):
            record_authentication_event(
                "LOGIN_FALHA", request=self.request, email=email, details={"motivo": "limite"}
            )
            raise ValidationError("E-mail ou senha inválidos.", code="invalid_login")
        try:
            cleaned_data = super().clean()
        except ValidationError:
            record_login_failure(email)
            record_authentication_event(
                "LOGIN_FALHA", request=self.request, email=email, details={"motivo": "credencial"}
            )
            raise
        return cleaned_data


class AccountCreationForm(UserCreationForm):
    email = NormalizedRegistrationEmailField()

    class Meta:
        model = User
        fields = ("email", "full_name", "profile", "status", "must_change_password")


class AccountChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


class AccountPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_password_input_limits(self, ("new_password1", "new_password2"))


class AccountSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_password_input_limits(self, ("new_password1", "new_password2"))


class FiscalRegistrationForm(UserCreationForm):
    email = NormalizedRegistrationEmailField()
    full_name = forms.CharField(label="Nome completo", max_length=200)
    organization_name = forms.CharField(label="Organização", max_length=200)
    sector_name = forms.CharField(label="Setor", max_length=200, required=False)
    phone = forms.CharField(label="Telefone", max_length=30, required=False)

    class Meta:
        model = User
        fields = (
            "full_name",
            "email",
            "organization_name",
            "sector_name",
            "phone",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_password_input_limits(self, ("password1", "password2"))

    def clean_email(self):
        email = User.objects.normalize_login_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe uma conta com este e-mail.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError("FiscalRegistrationForm exige commit=True.")
        from contracts.models import (
            ContractInvitation,
            ContractInvitationStatus,
            FiscalSubstitution,
            FiscalSubstitutionStatus,
        )

        has_pending_read_only_invitation = (
            ContractInvitation.objects.filter(
                email__iexact=self.cleaned_data["email"],
                status=ContractInvitationStatus.PENDING,
            )
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
            .exists()
        )
        has_pending_fiscal_substitution = FiscalSubstitution.objects.filter(
            email__iexact=self.cleaned_data["email"],
            status=FiscalSubstitutionStatus.PENDING_ACCOUNT,
            ends_on__gte=timezone.localdate(),
        ).exists()
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            full_name=self.cleaned_data["full_name"],
            organization_name=self.cleaned_data["organization_name"],
            sector_name=self.cleaned_data["sector_name"],
            phone=self.cleaned_data["phone"],
            password=self.cleaned_data["password1"],
            profile=(
                UserProfile.CONSULTATION
                if has_pending_read_only_invitation
                and not has_pending_fiscal_substitution
                else UserProfile.FISCAL
            ),
            status=AccountStatus.PENDING_APPROVAL,
        )
        RegistrationRequest.objects.create(user=user)
        return user


class AdministrativeFiscalCreationForm(UserCreationForm):
    email = NormalizedRegistrationEmailField()
    organization = forms.ModelChoiceField(
        label="Organização", queryset=Organization.objects.none()
    )
    sector = forms.ModelChoiceField(
        label="Setor", queryset=Sector.objects.none(), required=False
    )
    phone = forms.CharField(label="Telefone", max_length=30, required=False)

    class Meta:
        model = User
        fields = (
            "full_name",
            "email",
            "organization",
            "sector",
            "phone",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        apply_password_input_limits(self, ("password1", "password2"))
        self.fields["organization"].queryset = Organization.objects.filter(is_active=True)
        self.fields["sector"].queryset = Sector.objects.filter(
            is_active=True, organization__is_active=True
        ).select_related("organization")

    def clean_email(self):
        email = User.objects.normalize_login_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get("organization")
        sector = cleaned_data.get("sector")
        if sector and organization and sector.organization_id != organization.pk:
            self.add_error("sector", "O setor deve pertencer à organização selecionada.")
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            raise ValueError("AdministrativeFiscalCreationForm exige commit=True.")
        organization = Organization.objects.select_for_update().get(
            pk=self.cleaned_data["organization"].pk, is_active=True
        )
        sector = None
        if self.cleaned_data["sector"]:
            sector = Sector.objects.select_for_update().get(
                pk=self.cleaned_data["sector"].pk,
                organization=organization,
                is_active=True,
            )
        return User.objects.create_user(
            email=self.cleaned_data["email"],
            full_name=self.cleaned_data["full_name"],
            organization=organization,
            sector=sector,
            organization_name=organization.name,
            sector_name=sector.name if sector else "",
            phone=self.cleaned_data["phone"],
            password=self.cleaned_data["password1"],
            profile=UserProfile.FISCAL,
            status=AccountStatus.ACTIVE,
            must_change_password=True,
        )


class RegistrationReviewForm(forms.Form):
    action = forms.ChoiceField(
        choices=(("approve", "Aprovar"), ("reject", "Rejeitar")),
        widget=forms.HiddenInput,
    )
    rejection_reason = forms.CharField(
        label="Motivo da rejeição", required=False, max_length=2000, widget=forms.Textarea
    )
    organization = forms.ModelChoiceField(
        label="Organização para vínculo", queryset=Organization.objects.none(), required=False
    )
    sector = forms.ModelChoiceField(
        label="Setor para vínculo", queryset=Sector.objects.none(), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = Organization.objects.filter(is_active=True)
        self.fields["sector"].queryset = Sector.objects.filter(
            is_active=True, organization__is_active=True
        ).select_related("organization")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("action") == "reject" and not cleaned_data.get(
            "rejection_reason", ""
        ).strip():
            self.add_error("rejection_reason", "Informe o motivo da rejeição.")
        if cleaned_data.get("action") == "approve":
            organization = cleaned_data.get("organization")
            sector = cleaned_data.get("sector")
            if not organization:
                self.add_error("organization", "Selecione a organização do Fiscal.")
            if sector and organization and sector.organization_id != organization.pk:
                self.add_error("sector", "O setor deve pertencer à organização selecionada.")
        return cleaned_data


class UserOrganizationAssignmentForm(forms.Form):
    organization = forms.ModelChoiceField(
        label="Organização", queryset=Organization.objects.none()
    )
    sector = forms.ModelChoiceField(
        label="Setor", queryset=Sector.objects.none(), required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["organization"].queryset = Organization.objects.filter(is_active=True)
        self.fields["sector"].queryset = Sector.objects.filter(
            is_active=True, organization__is_active=True
        ).select_related("organization")

    def clean(self):
        cleaned_data = super().clean()
        organization = cleaned_data.get("organization")
        sector = cleaned_data.get("sector")
        if sector and organization and sector.organization_id != organization.pk:
            self.add_error("sector", "O setor deve pertencer à organização selecionada.")
        return cleaned_data
