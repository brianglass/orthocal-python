import logging

from django.apps import apps
from django.conf import settings
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views import generic

from .apps import OrthocalConfig
from .decorators import etag

logger = logging.getLogger(__name__)

async def startup_probe(request, *args, **kwargs):
    app_config = apps.get_app_config(OrthocalConfig.name)
    if app_config.orthocal_started:
        return JsonResponse({'started': True})
    else:
        return JsonResponse({'started': False}, status=500)

@etag
async def alexa(request):
    return TemplateResponse(request, 'alexa.html')

@etag
async def api(request):
    return TemplateResponse(request, 'api.html')

@etag
async def ai_assistant(request):
    return TemplateResponse(request, 'ai_assistant.html')

@etag
async def mcp_server_card(request):
    """MCP Server Card discovery metadata (SEP-2127, still a draft proposal as
    of 2026-08 -- field names/path may still change before the spec finalizes).
    Lets a client learn the server's name/tools/capabilities before opening a
    full MCP connection."""

    from mcp_svc.server import mcp

    return JsonResponse({
        'name': 'info.orthocal.mcp',
        'title': mcp.name,
        'description': mcp.instructions,
        'websiteUrl': settings.ORTHOCAL_PUBLIC_URL,
        'remotes': [
            {
                'url': f'{settings.ORTHOCAL_PUBLIC_URL}/mcp',
                'transport': 'streamable-http',
            },
        ],
    })

@etag
async def feeds(request):
    return TemplateResponse(request, 'feeds.html')

@etag
async def about(request):
    return TemplateResponse(request, 'about.html')
