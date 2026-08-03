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
from mcp.server.transport_security import TransportSecuritySettings

django_application = get_asgi_application()

# mcp_svc.server.mcp imports Django models, so it can only be constructed
# after get_asgi_application() has set up Django.
from mcp_svc.server import mcp

# MCPServer.streamable_http_app() returns a complete Starlette app -- it
# owns its own /mcp route and lifespan (which starts/stops its session
# manager's background task). Django's ASGIHandler doesn't implement the
# lifespan protocol at all, so lifespan scope is only ever handled here.
#
# transport_security must be set explicitly: with no host argument, the SDK
# defaults host to '127.0.0.1' and auto-enables DNS-rebinding protection
# restricted to localhost -- fine in local dev, but it rejects every real
# request in production (Cloud Run's own hostname as the Host header,
# forwarded by the Firebase Hosting proxy in front of it, isn't on that
# allowlist). DNS-rebinding protection defends a server bound to localhost
# against a malicious webpage's JS reaching it through the browser; it
# doesn't apply to a public HTTPS API with no localhost-only trust boundary,
# so disabling it here is the correct fix, not a workaround.
mcp_application = mcp.streamable_http_app(
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


async def application(scope, receive, send):
    if scope['type'] == 'lifespan' or (scope['type'] == 'http' and scope['path'].startswith('/mcp')):
        await mcp_application(scope, receive, send)
    else:
        await django_application(scope, receive, send)
