from urllib.parse import parse_qs

from django.contrib.auth import get_user_model
from django.db import close_old_connections
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
from channels.db import database_sync_to_async

User = get_user_model()


@database_sync_to_async
def get_user_for_token(token):
    try:
        UntypedToken(token)
    except (InvalidToken, TokenError):
        return None
    try:
        decoded = jwt_decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None
    user_id = decoded.get('user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


class JwtAuthMiddleware:
    """JWT auth middleware for websocket connections."""
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JwtAuthMiddlewareInstance(scope, self)


class JwtAuthMiddlewareInstance:
    def __init__(self, scope, middleware):
        self.scope = dict(scope)
        self.middleware = middleware

    async def __call__(self, receive, send):
        close_old_connections()
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]
        if not token:
            headers = dict(self.scope.get('headers') or [])
            auth_header = headers.get(b'authorization')
            if auth_header:
                try:
                    auth_value = auth_header.decode()
                except Exception:
                    auth_value = ''
                if auth_value.lower().startswith('bearer '):
                    token = auth_value.split(' ', 1)[1].strip()
        user = None
        if token:
            user = await get_user_for_token(token)
        self.scope['user'] = user
        return await self.middleware.inner(self.scope, receive, send)
