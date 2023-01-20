from django.urls import path

from .ical import ical
from .api import api
from .feeds import ReadingsFeed

urlpatterns = [
    path('', api.urls),
    path('<cal:cal>/ical/', ical, name='ical'),
    path('feed/', ReadingsFeed(), name='feed'),
]
