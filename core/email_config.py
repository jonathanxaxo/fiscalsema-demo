"""Configuração de e-mail por variáveis de ambiente (Sprint 26).

SMTP só é ligado quando usuário e senha do servidor existem; caso contrário o
envio continua fictício (nada é enviado). A senha nunca é registrada.
"""

DUMMY_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
SMTP_BACKEND = "django.core.mail.backends.smtp.EmailBackend"


def email_settings(env):
    user = env.get("EMAIL_HOST_USER", "").strip()
    password = env.get("EMAIL_HOST_PASSWORD", "")
    enabled = bool(user and password)
    return {
        "EMAIL_BACKEND": SMTP_BACKEND if enabled else DUMMY_BACKEND,
        "EMAIL_HOST": env.get("EMAIL_HOST", "smtp.gmail.com").strip(),
        "EMAIL_PORT": int(env.get("EMAIL_PORT", "587")),
        "EMAIL_HOST_USER": user,
        "EMAIL_HOST_PASSWORD": password,
        "EMAIL_USE_TLS": env.get("EMAIL_USE_TLS", "True").strip().lower() in {"1", "true", "yes", "on"},
        "EMAIL_TIMEOUT": int(env.get("EMAIL_TIMEOUT", "10")),
        "DEFAULT_FROM_EMAIL": env.get("DEFAULT_FROM_EMAIL", "").strip()
        or (f"FiscalSema Demo <{user}>" if user else "nao-responder@fiscalsema.local"),
    }
