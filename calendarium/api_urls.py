from django.conf import settings
from django.urls import path
from django.views.decorators.cache import cache_page

from .ical import ical
from .api import api
from .feeds import ReadingsFeed

cache = cache_page(settings.ORTHOCAL_MAX_AGE)

urlpatterns = [
    path('', api.urls),
    path('<cal:cal>/ical/', ical, name='ical'),
    path('feed/', cache(ReadingsFeed()), name='rss-feed'),
    path('feed/<cal:cal>/', cache(ReadingsFeed()), name='rss-feed-cal'),
]
