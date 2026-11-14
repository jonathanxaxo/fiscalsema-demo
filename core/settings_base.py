import os
from pathlib import Path

import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
APP_ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "demo").strip().lower()
if APP_ENVIRONMENT not in {"demo", "production", "homologation"}:
    raise ValueError("APP_ENVIRONMENT deve ser demo, production ou homologation.")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
)

INSTALLED_APPS = [
    "api_v1.apps.ApiV1Config",
    "accounts.apps.AccountsConfig",
    "organizations.apps.OrganizationsConfig",
    "contracts.apps.ContractsConfig",
    "documents.apps.DocumentsConfig",
    "audit.apps.AuditConfig",
    "data_imports.apps.DataImportsConfig",
    "assistant.apps.AssistantConfig",
    "core.apps.CoreConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.RequirePasswordChangeMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.application_environment",
                "core.context_processors.topbar_notifications",
                "accounts.profile_switch.profile_switch",
                "assistant.context_processors.assistant_menu",
            ],
        },
    }
]

if os.getenv("DATABASE_URL"):
    DATABASES = {
        "default": dj_database_url.config(
            env="DATABASE_URL",
            conn_max_age=env_int("DATABASE_CONN_MAX_AGE", 60),
            conn_health_checks=True,
        )
    }
    DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = env_int(
        "DATABASE_CONNECT_TIMEOUT", 5
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DATABASE_NAME"],
            "USER": os.environ["DATABASE_USER"],
            "PASSWORD": os.environ["DATABASE_PASSWORD"],
            "HOST": os.getenv("DATABASE_HOST", "db"),
            "PORT": os.getenv("DATABASE_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DATABASE_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": {"connect_timeout": env_int("DATABASE_CONNECT_TIMEOUT", 5)},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 6},
    },
    {
        "NAME": "accounts.validators.MaximumLengthValidator",
        "OPTIONS": {"max_length": 24},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "accounts.validators.PasswordComplexityValidator"},
    {"NAME": "accounts.validators.PasswordDifferentFromEmailValidator"},
]

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.AccountStatusBackend"]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "accounts:login"
AUTH_LOGIN_MAX_FAILURES = env_int("AUTH_LOGIN_MAX_FAILURES", 5)
AUTH_LOGIN_WINDOW_SECONDS = env_int("AUTH_LOGIN_WINDOW_SECONDS", 900)
AUTH_LOGIN_BLOCK_SECONDS = env_int("AUTH_LOGIN_BLOCK_SECONDS", 900)
API_RATE_LIMIT_PER_MINUTE = env_int("API_RATE_LIMIT_PER_MINUTE", 60)
API_DEFAULT_PAGE_SIZE = env_int("API_DEFAULT_PAGE_SIZE", 25)
API_MAX_PAGE_SIZE = env_int("API_MAX_PAGE_SIZE", 100)

# Login com Google (Sprint 25): OpenID Connect próprio, sem dependência.
# O segredo fica só em variável de ambiente; sem as duas variáveis o botão não aparece.
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_TIMEOUT_SECONDS = env_int("GOOGLE_OAUTH_TIMEOUT_SECONDS", 10)

# Assistente Arise (Sprint 21). A chave fica só no backend, em variável de ambiente.
ASSISTANT_ENABLED = env_bool("ASSISTANT_ENABLED", False)
ASSISTANT_API_KEY = os.getenv("ASSISTANT_API_KEY", "")
ASSISTANT_BASE_URL = os.getenv(
    "ASSISTANT_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"
)
ASSISTANT_MODELS = env_list("ASSISTANT_MODELS")
ASSISTANT_TIMEOUT_SECONDS = env_int("ASSISTANT_TIMEOUT_SECONDS", 12)
ASSISTANT_DAILY_LIMIT = env_int("ASSISTANT_DAILY_LIMIT", 60)
ASSISTANT_PER_MINUTE = env_int("ASSISTANT_PER_MINUTE", 6)
ASSISTANT_RETENTION_DAYS = env_int("ASSISTANT_RETENTION_DAYS", 30)

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.dummy.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "nao-responder@fiscalsema.local")

LANGUAGE_CODE = "pt-br"
USE_THOUSAND_SEPARATOR = True
TIME_ZONE = "America/Cuiaba"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = Path(os.getenv("DJANGO_STATIC_ROOT", "/app/staticfiles"))
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.getenv("DJANGO_MEDIA_ROOT", "/app/media"))
DOCUMENT_MAX_UPLOAD_SIZE = env_int("DOCUMENT_MAX_UPLOAD_SIZE", 20 * 1024 * 1024)
SPREADSHEET_MAX_UPLOAD_SIZE = env_int(
    "SPREADSHEET_MAX_UPLOAD_SIZE", 5 * 1024 * 1024
)
FILE_FEATURES_ENABLED = env_bool("FILE_FEATURES_ENABLED", True)
PUBLIC_REGISTRATION_ENABLED = env_bool("PUBLIC_REGISTRATION_ENABLED", True)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_NAME = "fiscalsema_sessionid"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_NAME = "fiscalsema_csrftoken"
X_FRAME_OPTIONS = "DENY"

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO").upper()
FILE_LOGGING_ENABLED = env_bool(
    "DJANGO_FILE_LOGGING", APP_ENVIRONMENT != "demo"
)
LOG_HANDLERS = {
    "console": {"class": "logging.StreamHandler", "formatter": "standard"}
}
if FILE_LOGGING_ENABLED:
    LOG_DIR = Path(os.getenv("DJANGO_LOG_DIR", "/app/logs"))
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOG_HANDLERS["file"] = {
        "class": "logging.handlers.WatchedFileHandler",
        "filename": LOG_DIR / "django.log",
        "formatter": "standard",
    }
ACTIVE_LOG_HANDLERS = list(LOG_HANDLERS)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": LOG_HANDLERS,
    "root": {"handlers": ACTIVE_LOG_HANDLERS, "level": LOG_LEVEL},
    "loggers": {
        "django.security": {
            "handlers": ACTIVE_LOG_HANDLERS,
            "level": "WARNING",
            "propagate": False,
        }
    },
}
