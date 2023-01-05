from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import api

urlpatterns = [
    path('oca/<int:year>/<int:month>/<int:day>/', api.DayViewSet.as_view({'get': 'retrieve'})),
    path('oca/<int:year>/<int:month>/', api.DayViewSet.as_view({'get': 'list'})),
]

urlpatterns = format_suffix_patterns(urlpatterns)
