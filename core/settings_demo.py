import os
import ipaddress
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


dedicated_database_url = os.getenv("FISCALSEMA_DEMO_DATABASE_URL", "").strip()
if dedicated_database_url:
    os.environ["DATABASE_URL"] = dedicated_database_url

from .settings_base import *  # noqa: F403
from .settings_base import BASE_DIR, env_bool, env_list


if APP_ENVIRONMENT != "demo":  # noqa: F405
    raise ImproperlyConfigured("A configuração Vercel exige APP_ENVIRONMENT=demo.")

if not os.getenv("DATABASE_URL"):
    raise ImproperlyConfigured("DATABASE_URL é obrigatória no ambiente demo.")

database = DATABASES["default"]  # noqa: F405
database_name = str(database.get("NAME", "")).casefold()
database_user = str(database.get("USER", "")).casefold()
database_host = str(database.get("HOST", "")).casefold()
blocked_hosts = {
    "127.0.0.1",
    "db",
    "localhost",
}
if "demo" not in database_name or "demo" not in database_user:
    raise ImproperlyConfigured(
        "Isolamento recusado: banco e usuário de execução devem conter 'demo'."
    )
if database_host in blocked_hosts:
    raise ImproperlyConfigured(
        "Isolamento recusado: DATABASE_URL aponta para um host local ou da VM."
    )
try:
    database_ip = ipaddress.ip_address(database_host)
except ValueError:
    database_ip = None
if database_ip and not database_ip.is_global:
    raise ImproperlyConfigured(
        "Isolamento recusado: DATABASE_URL usa um endereço IP não público."
    )
sslmode = str(database.get("OPTIONS", {}).get("sslmode", "")).casefold()
if sslmode not in {"require", "verify-ca", "verify-full"}:
    raise ImproperlyConfigured(
        "Isolamento recusado: DATABASE_URL deve exigir TLS com sslmode."
    )

vercel_host = os.getenv("VERCEL_URL", "").strip().lower()
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
)
if vercel_host:
    if vercel_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(vercel_host)
    vercel_origin = f"https://{vercel_host}"
    if vercel_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(vercel_origin)

DEBUG = False
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "fiscalsema_demo_sessionid"
CSRF_COOKIE_NAME = "fiscalsema_demo_csrftoken"
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_ROOT = Path("/tmp/fiscalsema-demo-media")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.memory.InMemoryStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

FILE_FEATURES_ENABLED = False
PUBLIC_REGISTRATION_ENABLED = False
DOCUMENT_MAX_UPLOAD_SIZE = 4 * 1024 * 1024
SPREADSHEET_MAX_UPLOAD_SIZE = 4 * 1024 * 1024
EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
