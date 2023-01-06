from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from . import api

urlpatterns = [
    path('oca/<int:year>/<int:month>/<int:day>/', api.DayViewSet.as_view({'get': 'retrieve'}), {'jurisdiction': 'oca'}),
    path('oca/<int:year>/<int:month>/', api.DayViewSet.as_view({'get': 'list'}), {'jurisdiction': 'oca'}),
    path('rocor/<int:year>/<int:month>/<int:day>/', api.DayViewSet.as_view({'get': 'retrieve'}), {'jurisdiction': 'rocor'}),
    path('rocor/<int:year>/<int:month>/', api.DayViewSet.as_view({'get': 'list'}), {'jurisdiction': 'rocor'}),
    path('<juris:jurisdiction>/ical/', api.ical, name='ical'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
