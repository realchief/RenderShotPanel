"""
ASGI config for rendershot_django project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os
import dotenv
import django

dotenv.load_dotenv(f"{os.path.join(os.path.dirname(os.path.dirname(__file__)))}/.env")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rendershot_django.settings_package.production')
if os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = os.getenv('DJANGO_SETTINGS_MODULE')

django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import job.routing as job_routing
import system.routing as system_routing
from rendershot_django.token_auth import TokenAuthMiddlewareStack


routes = {"http": get_asgi_application(),
          "websocket": TokenAuthMiddlewareStack(URLRouter(job_routing.websocket_urlpatterns +
                                                          system_routing.websocket_urlpatterns))}

application = ProtocolTypeRouter(routes)
