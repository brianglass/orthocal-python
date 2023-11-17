from django.apps import apps 
from django.http import JsonResponse

from .apps import OrthocalConfig

async def startup_probe(request, *args, **kwargs):
    app_config = apps.get_app_config(OrthocalConfig.name)
    if app_config.orthocal_started:
        return JsonResponse({'started': True})
    else:
        return JsonResponse({'started': False}, status=500)
