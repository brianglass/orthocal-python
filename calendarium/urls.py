from django.conf import settings
from django.urls import path
from django.views.decorators.cache import cache_page
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from . import views

cache = cache_page(settings.ORTHOCAL_MAX_AGE)

urlpatterns = [
    path('readings/<cal:cal>/<year:year>/<month:month>/<day:day>/', views.readings_view, name='readings'),
    # Eventually we can remove this redirect, but we're still getting traffic here from crawlers.
    path('calendar/<cal:cal>/<year:year>/<month:month>/<day:day>/', RedirectView.as_view(permanent=True, pattern_name='readings')),
    path('calendar/<cal:cal>/<year:year>/<month:month>/', cache(views.calendar_view), name='calendar'),
    path('calendar-embed/<cal:cal>/<year:year>/<month:month>/', views.calendar_embed_view, name='calendar-embed'),
    path('calendar-embed/', views.calendar_embed_view, name='calendar-embed-default'),
    path('calendar/', views.calendar_view, name='calendar-default'),
    path('lectionary/', views.lectionary, name='lectionary'),
    path('', views.readings_view, name='index'),
]
