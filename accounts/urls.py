from django.conf import settings
from django.contrib.auth.views import PasswordChangeDoneView
from django.urls import path

from . import google_views
from .profile_switch import SwitchProfileView
from .views import (
    AccountLoginView,
    AccountLogoutView,
    AccountPasswordChangeView,
    AccountPasswordResetCompleteView,
    AccountPasswordResetConfirmView,
    AccountPasswordResetDoneView,
    AccountPasswordResetView,
    FiscalRegistrationView,
    RegistrationSubmittedView,
)

app_name = "accounts"

urlpatterns = [
    path("entrar/", AccountLoginView.as_view(), name="login"),
    path("sair/", AccountLogoutView.as_view(), name="logout"),
    path("perfil/alternar/", SwitchProfileView.as_view(), name="switch_profile"),
    path("minha-conta/", google_views.my_account, name="my_account"),
    path("google/entrar/", google_views.google_start, name="google_start"),
    path("google/retorno/", google_views.google_callback, name="google_callback"),
    path("google/cadastro/", google_views.google_signup, name="google_signup"),
    path("google/confirmar-vinculo/", google_views.google_confirm_link, name="google_confirm_link"),
    path("google/vincular/", google_views.google_link_start, name="google_link_start"),
    path("google/<int:pk>/desvincular/", google_views.google_unlink, name="google_unlink"),
    path("conexoes/<int:pk>/revogar/", google_views.mcp_revoke, name="mcp_revoke"),
    path("alterar-senha/", AccountPasswordChangeView.as_view(), name="password_change"),
    path(
        "alterar-senha/concluida/",
        PasswordChangeDoneView.as_view(template_name="accounts/password_change_done.html"),
        name="password_change_done",
    ),
    path("recuperar-senha/", AccountPasswordResetView.as_view(), name="password_reset"),
    path(
        "recuperar-senha/enviada/",
        AccountPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "redefinir-senha/<uidb64>/<token>/",
        AccountPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "redefinir-senha/concluida/",
        AccountPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]

if settings.PUBLIC_REGISTRATION_ENABLED:
    urlpatterns += [
        path("cadastrar/", FiscalRegistrationView.as_view(), name="register"),
        path(
            "cadastrar/enviado/",
            RegistrationSubmittedView.as_view(),
            name="registration_submitted",
        ),
    ]
