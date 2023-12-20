import logging

from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from . import views
from orthocal.decorators import cache, etag, etag_date, acache

logger = logging.getLogger(__name__)

urlpatterns = [
    path('readings/<cal:cal>/<year:year>/<month:month>/<day:day>/', acache(etag(views.readings_view)), name='readings'),
    # Eventually we can remove this redirect, but we're still getting traffic here from crawlers.
    path('calendar/<cal:cal>/<year:year>/<month:month>/<day:day>/', RedirectView.as_view(permanent=True, pattern_name='readings')),
    path('calendar/<cal:cal>/<year:year>/<month:month>/', acache(etag(views.calendar_view)), name='calendar'),
    path('calendar-embed/<cal:cal>/<year:year>/<month:month>/', views.calendar_embed_view, name='calendar-embed'),
    path('calendar-embed/', etag_date(views.calendar_embed_view), name='calendar-embed-default'),
    path('calendar/', etag_date(views.calendar_view), name='calendar-default'),
    path('', etag_date(views.readings_view), name='index'),
]
