from django.urls import path

from .views import ContractAuditView, GlobalAuditView


app_name = "audit"

urlpatterns = [
    path("", GlobalAuditView.as_view(), name="global"),
    path("contratos/<int:contract_pk>/", ContractAuditView.as_view(), name="contract"),
]
