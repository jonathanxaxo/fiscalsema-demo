import os

from .settings_base import *  # noqa: F403


DEBUG = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

DATABASES["default"]["CONN_MAX_AGE"] = 0  # noqa: F405
DATABASES["default"]["TEST"] = {  # noqa: F405
    "NAME": os.getenv("DATABASE_TEST_NAME", f"test_{DATABASES['default']['NAME']}")  # noqa: F405
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
LOGGING["handlers"] = {  # noqa: F405
    "console": {"class": "logging.StreamHandler", "formatter": "standard"}
}
LOGGING["root"] = {"handlers": ["console"], "level": "WARNING"}  # noqa: F405
LOGGING["loggers"]["django.security"] = {  # noqa: F405
    "handlers": ["console"],
    "level": "WARNING",
    "propagate": False,
}
