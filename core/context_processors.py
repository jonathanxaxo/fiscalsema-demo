from django.conf import settings


def application_environment(request):
    return {
        "app_environment": settings.APP_ENVIRONMENT,
        "is_homologation": settings.APP_ENVIRONMENT == "homologation",
        "is_demo": settings.APP_ENVIRONMENT == "demo",
        "file_features_enabled": settings.FILE_FEATURES_ENABLED,
        "public_registration_enabled": settings.PUBLIC_REGISTRATION_ENABLED,
        "google_login_enabled": bool(
            settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
        ),
        "session_idle_timeout": int(getattr(settings, "SESSION_IDLE_TIMEOUT_SECONDS", 0) or 0),
    }


def topbar_notifications(request):
    """Sino do topo: calculado somente se o template exibir as notificações."""
    from django.utils.functional import SimpleLazyObject

    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    # Dentro das telas de um contrato, o sino mostra somente aquele contrato:
    # dados de contratos diferentes nunca se misturam na mesma tela.
    contract_scope = None
    match = getattr(request, "resolver_match", None)
    if match is not None:
        contract_scope = match.kwargs.get("contract_pk")
        if contract_scope is None and match.app_name == "contracts":
            contract_scope = match.kwargs.get("pk")

    def load():
        from .notifications import build_notifications

        return build_notifications(user, contract_id=contract_scope)

    return {"topbar_notifications": SimpleLazyObject(load)}
