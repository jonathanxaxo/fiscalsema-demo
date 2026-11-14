from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("", views.chat, name="chat"),
    path("conversas/<int:pk>/", views.chat, name="conversation"),
    path("conversas/<int:pk>/excluir/", views.delete, name="delete"),
    path("perguntar/", views.ask, name="ask"),
]
