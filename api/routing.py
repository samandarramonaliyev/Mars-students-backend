from django.urls import re_path

from .consumers import ChessConsumer

websocket_urlpatterns = [
    re_path(r'^ws/chess/(?P<game_id>\d+)/$', ChessConsumer.as_asgi()),
]
