import hashlib
import logging

from django.conf import settings
from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.decorators.http import etag
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from . import views

logger = logging.getLogger(__name__)

cache = cache_page(settings.ORTHOCAL_MAX_AGE)

def get_etag(request, *args, **kwargs):
    hash = hashlib.md5()

    hash.update(settings.ORTHOCAL_REVISION.encode('utf8'))

    for header in settings.ORTHOCAL_VARY_HEADERS:
        if value := request.headers.get(header):
            hash.update(f'{header}: {value}'.encode('utf8'))

    return f'"{hash.hexdigest()}"'

etag = etag(get_etag)

urlpatterns = [
    path('readings/<cal:cal>/<year:year>/<month:month>/<day:day>/', etag(views.readings_view), name='readings'),
    # Eventually we can remove this redirect, but we're still getting traffic here from crawlers.
    path('calendar/<cal:cal>/<year:year>/<month:month>/<day:day>/', RedirectView.as_view(permanent=True, pattern_name='readings')),
    path('calendar/<cal:cal>/<year:year>/<month:month>/', cache(etag(views.calendar_view)), name='calendar'),
    path('calendar-embed/<cal:cal>/<year:year>/<month:month>/', views.calendar_embed_view, name='calendar-embed'),
    path('calendar-embed/', views.calendar_embed_view, name='calendar-embed-default'),
    path('calendar/', views.calendar_view, name='calendar-default'),
    path('', views.readings_view, name='index'),
]
