from django.apps import apps 
from django.http import JsonResponse
from django.views import generic

from .apps import OrthocalConfig

async def startup_probe(request, *args, **kwargs):
    app_config = apps.get_app_config(OrthocalConfig.name)
    if app_config.orthocal_started:
        return JsonResponse({'started': True})
    else:
        return JsonResponse({'started': False}, status=500)

# Make an async version of TemplateView
class TemplateView(generic.TemplateView):
    async def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

alexa = TemplateView.as_view(template_name='alexa.html')
api = TemplateView.as_view(template_name='api.html')
feeds = TemplateView.as_view(template_name='feeds.html')
about = TemplateView.as_view(template_name='about.html')
