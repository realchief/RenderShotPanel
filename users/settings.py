from django.conf import settings
from django.templatetags.static import static


def configure_default_settings():
    settings.GRAVATAR_SECURE = getattr(settings, 'GRAVATAR_SECURE', True)
    settings.GRAVATAR_DEFAULT_URL = getattr(settings, 'GRAVATAR_DEFAULT_URL', '')
