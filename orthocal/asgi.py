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
#
# stateless_http must also be set: the default session manager tracks each
# session's transport in that process's own memory, but Cloud Run scales
# this service to multiple instances (maxScale=15, no session affinity
# configured) with no guarantee a session's follow-up request lands back on
# the instance that created it -- confirmed via production logs showing
# several instances each starting their own independent session manager.
# Both tools are stateless reads, so there's no reason to need session
# affinity in the first place; stateless_http=True makes every request
# self-contained instead.
mcp_application = mcp.streamable_http_app(
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    stateless_http=True,
)


async def _reject_get(send):
    """Neither of orthocal's MCP tools ever needs to push an unsolicited
    message to a client, so the streamable-http transport's optional GET/SSE
    channel serves no purpose here -- but the SDK holds it open indefinitely
    waiting for a server-initiated message that will never come, and Cloud
    Run only closes it at the request timeout (20s). That turned into the
    single largest cost driver on this service: a flood of GET requests each
    billed for a full 20s of held-open compute. Rejecting GET here, before it
    reaches the MCP app, costs a few milliseconds instead."""

    await send({
        'type': 'http.response.start',
        'status': 405,
        'headers': [
            (b'allow', b'POST, DELETE'),
            (b'content-type', b'text/plain'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'Method Not Allowed',
    })


async def application(scope, receive, send):
    is_mcp_path = scope['type'] == 'http' and scope['path'].startswith('/mcp')
    if is_mcp_path and scope['method'] == 'GET':
        await _reject_get(send)
    elif scope['type'] == 'lifespan' or is_mcp_path:
        await mcp_application(scope, receive, send)
    else:
        await django_application(scope, receive, send)
