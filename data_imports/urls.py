from django.urls import path

from .views import ImportConfirmView, ImportDetailView, ImportMappingView, ImportUploadView


app_name = "data_imports"

urlpatterns = [
    path("contratos/<int:contract_pk>/", ImportUploadView.as_view(), name="upload"),
    path("contratos/<int:contract_pk>/<int:pk>/mapear/", ImportMappingView.as_view(), name="mapping"),
    path("contratos/<int:contract_pk>/<int:pk>/", ImportDetailView.as_view(), name="detail"),
    path("contratos/<int:contract_pk>/<int:pk>/confirmar/", ImportConfirmView.as_view(), name="confirm"),
]
