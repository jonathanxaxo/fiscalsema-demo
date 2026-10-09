from django.urls import path

from .views import (
    AdministrativeFiscalCreateView,
    AdministrativeUserArchiveView,
    AdministrativeUserListView,
    AdministrativeUserRestoreView,
    AdministrativeUserStatusView,
    RegistrationRequestArchiveView,
    RegistrationRequestListView,
    RegistrationRequestReviewView,
    UserOrganizationAssignmentView,
)


app_name = "accounts_admin"

urlpatterns = [
    path("usuarios/", AdministrativeUserListView.as_view(), name="user_list"),
    path("solicitacoes/", RegistrationRequestListView.as_view(), name="registration_list"),
    path(
        "solicitacoes/<int:pk>/",
        RegistrationRequestReviewView.as_view(),
        name="registration_review",
    ),
    path(
        "solicitacoes/<int:pk>/arquivar/",
        RegistrationRequestArchiveView.as_view(),
        name="registration_archive",
    ),
    path("usuarios/novo/", AdministrativeFiscalCreateView.as_view(), name="fiscal_create"),
    path(
        "usuarios/<int:pk>/status/<str:action>/",
        AdministrativeUserStatusView.as_view(),
        name="user_status",
    ),
    path(
        "usuarios/<int:pk>/excluir/",
        AdministrativeUserArchiveView.as_view(),
        name="user_archive",
    ),
    path(
        "usuarios/<int:pk>/restaurar/",
        AdministrativeUserRestoreView.as_view(),
        name="user_restore",
    ),
    path(
        "usuarios/<int:pk>/vinculo/",
        UserOrganizationAssignmentView.as_view(),
        name="user_organization",
    ),
]
