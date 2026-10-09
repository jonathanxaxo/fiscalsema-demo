from django.urls import path

from .web_views import (
    AssistantDraftBatchConfirmView, AssistantDraftConfirmView, AssistantDraftDetailView, AssistantDraftListView,
    AssistantDraftRejectView,
)


app_name = "assistant_drafts"
urlpatterns = [
    path("", AssistantDraftListView.as_view(), name="list"),
    path("lote/<uuid:batch_id>/confirmar/", AssistantDraftBatchConfirmView.as_view(), name="batch-confirm"),
    path("<int:pk>/", AssistantDraftDetailView.as_view(), name="detail"),
    path("<int:pk>/confirmar/", AssistantDraftConfirmView.as_view(), name="confirm"),
    path("<int:pk>/rejeitar/", AssistantDraftRejectView.as_view(), name="reject"),
]
