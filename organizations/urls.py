from django.urls import path

from .views import (
    OrganizationCreateView,
    OrganizationListView,
    OrganizationStatusView,
    OrganizationUpdateView,
    SectorCreateView,
    SectorListView,
    SectorStatusView,
    SectorUpdateView,
)


app_name = "organizations"

urlpatterns = [
    path("", OrganizationListView.as_view(), name="organization_list"),
    path("nova/", OrganizationCreateView.as_view(), name="organization_create"),
    path("<int:pk>/editar/", OrganizationUpdateView.as_view(), name="organization_update"),
    path("<int:pk>/status/", OrganizationStatusView.as_view(), name="organization_status"),
    path("setores/", SectorListView.as_view(), name="sector_list"),
    path("setores/novo/", SectorCreateView.as_view(), name="sector_create"),
    path("setores/<int:pk>/editar/", SectorUpdateView.as_view(), name="sector_update"),
    path("setores/<int:pk>/status/", SectorStatusView.as_view(), name="sector_status"),
]
