from django.urls import path

from .ical import ical
from .api import api

urlpatterns = [
    path('', api.urls),
    path('<cal:cal>/ical/', ical, name='ical'),
]
