import os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings_demo")

from core.wsgi import application  # noqa: E402


app = application
