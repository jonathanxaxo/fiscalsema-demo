from .provedor import is_configured


def assistant_menu(request):
    """Mostra o item "Assistente IA" no menu só quando o assistente está configurado."""
    return {"assistant_enabled": is_configured()}
