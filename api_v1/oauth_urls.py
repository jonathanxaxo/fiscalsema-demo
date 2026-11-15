"""Rotas OAuth/MCP publicadas (Sprint 28).

Só o necessário: metadados (RFC 8414/9728) na raiz, autorizar, token,
revogar e registro dinâmico. Não publicamos as telas de gestão de aplicativos,
introspecção nem fluxo de dispositivo. A gestão RFC 7592 do registro existe
porque a biblioteca a exige, mas só aceita o token de registro do próprio
cliente (válido por 1 hora) e não dá acesso a dados.
"""

from django.urls import path
from oauth2_provider import views as oauth_views
from oauth2_provider.urls import metadata_urlpatterns

app_name = "oauth2_provider"

urlpatterns = [
    *metadata_urlpatterns,
    path("oauth/authorize/", oauth_views.AuthorizationView.as_view(), name="authorize"),
    path("oauth/token/", oauth_views.TokenView.as_view(), name="token"),
    path("oauth/revoke_token/", oauth_views.RevokeTokenView.as_view(), name="revoke-token"),
    path("oauth/register/", oauth_views.DynamicClientRegistrationView.as_view(), name="dcr-register"),
    path(
        "oauth/register/<str:client_id>/",
        oauth_views.DynamicClientRegistrationManagementView.as_view(),
        name="dcr-register-management",
    ),
]
