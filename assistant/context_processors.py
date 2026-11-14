from .conhecimento import suggestions_for
from .provedor import is_configured


def assistant_menu(request):
    """Menu e ícone flutuante do Assistente Arise, só quando configurado e com login."""
    enabled = is_configured()
    user = getattr(request, "user", None)
    show_widget = bool(
        enabled
        and user is not None
        and user.is_authenticated
        and getattr(getattr(request, "resolver_match", None), "app_name", "") != "assistant"
    )
    return {
        "assistant_enabled": enabled,
        "assistant_widget": show_widget,
        "assistant_suggestions": suggestions_for(user.profile) if show_widget else (),
    }
