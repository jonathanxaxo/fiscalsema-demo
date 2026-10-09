from django.conf import settings


def application_environment(request):
    return {
        "app_environment": settings.APP_ENVIRONMENT,
        "is_homologation": settings.APP_ENVIRONMENT == "homologation",
        "is_demo": settings.APP_ENVIRONMENT == "demo",
        "file_features_enabled": settings.FILE_FEATURES_ENABLED,
        "public_registration_enabled": settings.PUBLIC_REGISTRATION_ENABLED,
    }
