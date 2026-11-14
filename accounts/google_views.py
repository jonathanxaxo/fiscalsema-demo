"""Login com Google, vínculo seguro e "Minha Conta" (Sprint 25).

Regras:
- identidade Google já vinculada → entra no MESMO usuário, respeitando a
  situação da conta;
- e-mail igual a um cadastro existente, sem vínculo → só vincula depois de a
  pessoa provar a posse da conta (senha atual do FiscalSema);
- sem cadastro → só e-mails autorizados (Sprint 27) completam um cadastro,
  que nasce pendente de aprovação do Administrador;
- nada do cadastro é alterado pelo vínculo (nome, perfil, organização,
  permissões, senha ou identificador).
"""

import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .backends import AccountStatusBackend
from .google_oidc import GoogleLoginError, complete_flow, is_configured, start_flow
from .forms import GoogleSignupForm, requested_profile_for
from .models import AccountStatus, AuthenticationEvent, ExternalIdentity, RegistrationRequest, User
from .signup_policy import is_signup_allowed
from .services import (
    clear_login_failures,
    is_login_blocked,
    record_authentication_event,
    record_login_failure,
)

AUTH_BACKEND = "accounts.backends.AccountStatusBackend"
PENDING_LINK_KEY = "fiscalsema_google_pending_link"
PENDING_LINK_SECONDS = 600
PENDING_SIGNUP_KEY = "fiscalsema_google_pending_signup"
EVENT = AuthenticationEvent.EventType


def _require_configured():
    if not is_configured():
        raise Http404("Login com Google não configurado.")


def _redirect_uri(request):
    return request.build_absolute_uri(reverse("accounts:google_callback"))


def _can_enter(user):
    return user.archived_at is None and AccountStatusBackend().user_can_authenticate(user)


def _status_message(user):
    if user.status == AccountStatus.PENDING_APPROVAL:
        return "Seu cadastro ainda aguarda aprovação do Administrador."
    return "Sua conta não está ativa. Procure o Administrador."


def _password_ok(request, user, password):
    """Confere a senha atual com o mesmo limite de tentativas do login."""
    if is_login_blocked(user.email):
        record_authentication_event(EVENT.LOGIN_FAILURE, request=request, email=user.email,
                                    details={"motivo": "limite", "origem": "google"})
        return False
    if password and user.has_usable_password() and user.check_password(password):
        clear_login_failures(user.email)
        return True
    record_login_failure(user.email)
    record_authentication_event(EVENT.LOGIN_FAILURE, request=request, email=user.email,
                                details={"motivo": "senha", "origem": "google"})
    return False


def _sign_in(request, user, identity):
    login(request, user, backend=AUTH_BACKEND)
    ExternalIdentity.objects.filter(pk=identity.pk).update(last_login_at=timezone.now())
    record_authentication_event(EVENT.GOOGLE_LOGIN, request=request, user=user, email=user.email,
                                details={"provedor": "google"})


@require_GET
def google_start(request):
    if not is_configured():
        messages.info(request, "O login com Google ainda está sendo configurado. Entre com e-mail e senha.")
        return redirect("accounts:login")
    if request.user.is_authenticated:
        return redirect("accounts:my_account")
    return redirect(start_flow(request.session, redirect_uri=_redirect_uri(request), intent="login"))


@require_GET
def google_callback(request):
    _require_configured()
    if request.GET.get("error"):
        request.session.pop("fiscalsema_google_oidc", None)
        messages.info(request, "Login com Google cancelado.")
        return redirect("accounts:login")
    try:
        google, flow = complete_flow(request.session, state=request.GET.get("state"), code=request.GET.get("code"))
    except GoogleLoginError as error:
        record_authentication_event(EVENT.GOOGLE_LOGIN_DENIED, request=request, details={"motivo": "validacao"})
        messages.error(request, str(error))
        return redirect("accounts:my_account" if request.user.is_authenticated else "accounts:login")

    existing = ExternalIdentity.objects.select_related("user").filter(
        provider=ExternalIdentity.Provider.GOOGLE, subject=google.subject
    ).first()

    if flow.get("intent") == "link":
        if not request.user.is_authenticated or request.user.pk != flow.get("user_id"):
            messages.error(request, "Entre novamente para vincular a conta Google.")
            return redirect("accounts:login")
        if existing:
            if existing.user_id == request.user.pk:
                messages.info(request, "Esta conta Google já está vinculada à sua conta.")
            else:
                record_authentication_event(EVENT.GOOGLE_LOGIN_DENIED, request=request, user=request.user,
                                            email=request.user.email, details={"motivo": "google_de_outro_usuario"})
                messages.error(request, "Esta conta Google já está vinculada a outro usuário.")
            return redirect("accounts:my_account")
        ExternalIdentity.objects.create(
            user=request.user, provider=ExternalIdentity.Provider.GOOGLE,
            subject=google.subject, email=google.email,
        )
        record_authentication_event(EVENT.GOOGLE_LINKED, request=request, user=request.user,
                                    email=request.user.email, details={"provedor": "google"})
        messages.success(request, "Conta Google vinculada.")
        return redirect("accounts:my_account")

    if existing:
        user = existing.user
        if not _can_enter(user):
            record_authentication_event(EVENT.GOOGLE_LOGIN_DENIED, request=request, user=user, email=user.email,
                                        details={"motivo": "conta_" + user.status.lower()})
            messages.error(request, _status_message(user))
            return redirect("accounts:login")
        _sign_in(request, user, existing)
        return redirect(settings.LOGIN_REDIRECT_URL)

    user = User.objects.filter(email=User.objects.normalize_login_email(google.email), archived_at__isnull=True).first()
    if user is not None:
        request.session[PENDING_LINK_KEY] = {
            "subject": google.subject, "email": google.email,
            "user_id": user.pk, "expires": int(time.time()) + PENDING_LINK_SECONDS,
        }
        return redirect("accounts:google_confirm_link")

    if is_signup_allowed(google.email, hosted_domain=google.hosted_domain):
        request.session[PENDING_SIGNUP_KEY] = {
            "subject": google.subject, "email": google.email, "name": google.name,
            "expires": int(time.time()) + PENDING_LINK_SECONDS,
        }
        return redirect("accounts:google_signup")

    record_authentication_event(EVENT.GOOGLE_LOGIN_DENIED, request=request, email=google.email,
                                details={"motivo": "email_nao_autorizado"})
    messages.error(
        request,
        "Não encontramos cadastro com este e-mail e ele não está autorizado a se cadastrar. "
        "Procure o Administrador do sistema.",
    )
    return redirect("accounts:login")


@require_http_methods(["GET", "POST"])
def google_signup(request):
    """Cadastro institucional pelo Google (Sprint 27): conta nasce pendente de aprovação."""
    _require_configured()
    pending = request.session.get(PENDING_SIGNUP_KEY)
    if not pending or pending.get("expires", 0) < time.time():
        request.session.pop(PENDING_SIGNUP_KEY, None)
        messages.error(request, "O cadastro expirou. Entre com o Google novamente.")
        return redirect("accounts:login")
    if request.method == "POST":
        form = GoogleSignupForm(request.POST)
    else:
        form = GoogleSignupForm(initial={"full_name": pending.get("name", "")})
    if request.method == "POST" and form.is_valid():
        email = User.objects.normalize_login_email(pending["email"])
        if not is_signup_allowed(email):
            request.session.pop(PENDING_SIGNUP_KEY, None)
            messages.error(request, "Este e-mail não está autorizado a se cadastrar.")
            return redirect("accounts:login")
        try:
            with transaction.atomic():
                if User.objects.filter(email__iexact=email).exists():
                    raise IntegrityError("e-mail já cadastrado")
                user = User(
                    email=email,
                    full_name=form.cleaned_data["full_name"],
                    organization_name=form.cleaned_data["organization_name"],
                    sector_name=form.cleaned_data["sector_name"],
                    phone=form.cleaned_data["phone"],
                    profile=requested_profile_for(email),
                    status=AccountStatus.PENDING_APPROVAL,
                )
                user.set_unusable_password()
                user.full_clean(exclude={"password"})
                user.save()
                registration = RegistrationRequest.objects.create(user=user)
                ExternalIdentity.objects.create(
                    user=user, provider=ExternalIdentity.Provider.GOOGLE,
                    subject=pending["subject"], email=email,
                )
        except IntegrityError:
            request.session.pop(PENDING_SIGNUP_KEY, None)
            messages.error(request, "Já existe uma conta com este e-mail ou esta conta Google. Entre novamente.")
            return redirect("accounts:login")
        request.session.pop(PENDING_SIGNUP_KEY, None)
        record_authentication_event(
            EVENT.REGISTRATION_REQUESTED, request=request, user=user, email=user.email,
            details={"solicitacao_id": registration.pk, "perfil_solicitado": user.profile, "origem": "google"},
        )
        return render(request, "accounts/registration_submitted.html")
    return render(request, "accounts/google_signup.html", {"form": form, "google_email": pending["email"]})


@require_http_methods(["GET", "POST"])
def google_confirm_link(request):
    """Prova de posse: a pessoa confirma a senha atual da conta existente."""
    _require_configured()
    pending = request.session.get(PENDING_LINK_KEY)
    if not pending or pending.get("expires", 0) < time.time():
        request.session.pop(PENDING_LINK_KEY, None)
        messages.error(request, "A confirmação expirou. Entre com o Google novamente.")
        return redirect("accounts:login")
    user = User.objects.filter(pk=pending["user_id"], archived_at__isnull=True).first()
    if user is None:
        request.session.pop(PENDING_LINK_KEY, None)
        return redirect("accounts:login")
    context = {"google_email": pending["email"], "has_password": user.has_usable_password()}
    if request.method == "GET":
        return render(request, "accounts/google_confirm_link.html", context)

    if not _password_ok(request, user, request.POST.get("password", "")):
        context["error"] = "Senha incorreta ou muitas tentativas. Tente novamente mais tarde."
        return render(request, "accounts/google_confirm_link.html", context, status=400)
    if not _can_enter(user):
        request.session.pop(PENDING_LINK_KEY, None)
        messages.error(request, _status_message(user))
        return redirect("accounts:login")
    try:
        with transaction.atomic():
            identity = ExternalIdentity.objects.create(
                user=user, provider=ExternalIdentity.Provider.GOOGLE,
                subject=pending["subject"], email=pending["email"],
            )
    except IntegrityError:
        request.session.pop(PENDING_LINK_KEY, None)
        messages.error(request, "Esta conta Google já foi vinculada. Entre com o Google novamente.")
        return redirect("accounts:login")
    request.session.pop(PENDING_LINK_KEY, None)
    record_authentication_event(EVENT.GOOGLE_LINKED, request=request, user=user, email=user.email,
                                details={"provedor": "google", "prova_de_posse": "senha"})
    _sign_in(request, user, identity)
    messages.success(request, "Conta Google vinculada ao seu cadastro.")
    return redirect(settings.LOGIN_REDIRECT_URL)


@login_required
@require_GET
def my_account(request):
    return render(
        request,
        "accounts/my_account.html",
        {
            "identities": request.user.external_identities.all(),
            "has_password": request.user.has_usable_password(),
            "google_enabled": is_configured(),
            "api_credentials": request.user.api_credentials.filter(revoked_at__isnull=True).order_by("name"),
        },
    )


@login_required
@require_POST
def google_link_start(request):
    _require_configured()
    if not _password_ok(request, request.user, request.POST.get("password", "")):
        messages.error(request, "Senha incorreta. Confirme sua senha para vincular a conta Google.")
        return redirect("accounts:my_account")
    url = start_flow(request.session, redirect_uri=_redirect_uri(request), intent="link", user_id=request.user.pk)
    return redirect(url)


@login_required
@require_POST
def google_unlink(request, pk):
    identity = get_object_or_404(ExternalIdentity, pk=pk, user=request.user)
    others = request.user.external_identities.exclude(pk=identity.pk).exists()
    if not request.user.has_usable_password() and not others:
        messages.error(request, "Não é possível desvincular: esta é a sua única forma de acesso.")
        return redirect("accounts:my_account")
    if not _password_ok(request, request.user, request.POST.get("password", "")):
        messages.error(request, "Senha incorreta. A conta Google continua vinculada.")
        return redirect("accounts:my_account")
    identity.delete()
    record_authentication_event(EVENT.GOOGLE_UNLINKED, request=request, user=request.user,
                                email=request.user.email, details={"provedor": "google"})
    messages.success(request, "Conta Google desvinculada.")
    return redirect("accounts:my_account")
