"""
ASGI config for orthocal project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')

from django.conf import settings
from django.core.asgi import get_asgi_application

django_application = get_asgi_application()

# mcp_svc.server.mcp imports Django models, so it can only be constructed
# after get_asgi_application() has set up Django.
from mcp_svc.server import mcp

# MCPServer.streamable_http_app() returns a complete Starlette app -- it
# owns its own /mcp route and lifespan (which starts/stops its session
# manager's background task). Django's ASGIHandler doesn't implement the
# lifespan protocol at all, so lifespan scope is only ever handled here.
mcp_application = mcp.streamable_http_app()


async def application(scope, receive, send):
    if scope['type'] == 'lifespan' or (scope['type'] == 'http' and scope['path'].startswith('/mcp')):
        await mcp_application(scope, receive, send)
    else:
        await django_application(scope, receive, send)
