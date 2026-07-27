from django.conf import settings
from django.urls import path
from django.views.decorators.cache import cache_page

from orthocal.decorators import cache

from .api import api
from .feeds import ReadingsFeed
from .ical import ical

urlpatterns = [
    path('', api.urls),
    path('<cal:cal>/ical/', ical, name='ical'),
    path('<tradition:tradition>/<cal:cal>/ical/', ical, name='ical'),
    path('feed/', cache(ReadingsFeed()), name='rss-feed'),
    path('feed/<cal:cal>/', cache(ReadingsFeed()), name='rss-feed-cal'),
    path('feed/<tradition:tradition>/<cal:cal>/', cache(ReadingsFeed()), name='rss-feed-cal'),
]
