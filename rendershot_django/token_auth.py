import logging
from channels.auth import AuthMiddlewareStack
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async


@database_sync_to_async
def get_user(token):
    try:
        return Token.objects.get(key=token.decode()).user
    except Token.DoesNotExist:
        return AnonymousUser()


class TokenAuthMiddleware:
    """
    Token authorization middleware for Django Channels 2
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):

        headers = dict(scope['headers'])
        # logging.info(f"headers from socket client : {headers}")
        if b'token' in headers:
            token = headers.get(b'token', b'')
            scope['user'] = await get_user(token)

        return await self.app(scope, receive, send)


def TokenAuthMiddlewareStack(inner):
    return TokenAuthMiddleware(AuthMiddlewareStack(inner))

