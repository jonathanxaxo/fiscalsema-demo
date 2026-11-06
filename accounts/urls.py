from django.conf import settings
from django.contrib.auth.views import PasswordChangeDoneView
from django.urls import path

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
