from django.urls import path

from .views import DocumentDownloadView, DocumentListView, DocumentUploadView


app_name = "documents"

urlpatterns = [
    path("contratos/<int:contract_pk>/", DocumentListView.as_view(), name="list"),
    path("contratos/<int:contract_pk>/novo/", DocumentUploadView.as_view(), name="upload"),
    path("<int:pk>/baixar/", DocumentDownloadView.as_view(), name="download"),
]
