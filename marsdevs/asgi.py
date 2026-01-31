"""
ASGI config for marsdevs project.
"""

import os

import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marsdevs.settings')

# Явно инициализируем Django перед импортом приложений
django.setup()

# Импорты после инициализации Django, чтобы приложения были загружены
from api.routing import websocket_urlpatterns  # noqa: E402
from api.ws_auth import JwtAuthMiddleware  # noqa: E402

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': JwtAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})
