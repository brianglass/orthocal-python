import logging

from django.apps import apps 
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
async def feeds(request):
    return TemplateResponse(request, 'feeds.html')

@etag
async def about(request):
    return TemplateResponse(request, 'about.html')
