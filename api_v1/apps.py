from django.apps import AppConfig


class ApiV1Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api_v1"
    verbose_name = "API segura v1"

    def ready(self):
        from oauth2_provider.signals import app_authorized

        from .oauth import record_authorization

        app_authorized.connect(record_authorization, dispatch_uid="fiscalsema_mcp_token")
