from django.urls import path
from django_ask_sdk.skill_adapter import SkillAdapter
from rest_framework.urlpatterns import format_suffix_patterns

from . import api

urlpatterns = [
    path('<cal:cal>/<int:year>/<int:month>/<int:day>/', api.DayViewSet.as_view({'get': 'retrieve'}), name='day-get'),
    path('<cal:cal>/<int:year>/<int:month>/', api.DayViewSet.as_view({'get': 'list'}), name='day-list'),
    path('<cal:cal>/', api.DayViewSet.as_view({'get': 'retrieve_default'}), name='day-get-default'),
    path('<cal:cal>/ical/', api.ical, name='ical'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
