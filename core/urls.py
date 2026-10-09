from django.contrib import admin
from django.urls import include, path

from .views import health, home


urlpatterns = [
    path("api/v1/", include("api_v1.urls")),
    path("rascunhos-ia/", include("api_v1.web_urls")),
    path("", home, name="home"),
    path("conta/", include("accounts.urls")),
    path("contratos/", include("contracts.urls")),
    path("documentos/", include("documents.urls")),
    path("auditoria/", include("audit.urls")),
    path("importacoes/", include("data_imports.urls")),
    path(
        "administracao/",
        include(("accounts.admin_urls", "accounts_admin"), namespace="accounts_admin"),
    ),
    path("administracao/organizacoes/", include("organizations.urls")),
    path("healthz", health, name="health"),
    path("admin/", admin.site.urls),
]
