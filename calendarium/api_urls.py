from django.urls import path
from django_ask_sdk.skill_adapter import SkillAdapter
from rest_framework.urlpatterns import format_suffix_patterns

from . import api, skills

orthodox_daily_view = SkillAdapter.as_view(skill=skills.orthodox_daily_skill)

urlpatterns = [
    path('<juris:jurisdiction>/<int:year>/<int:month>/<int:day>/', api.DayViewSet.as_view({'get': 'retrieve'}), name='day-get'),
    path('<juris:jurisdiction>/<int:year>/<int:month>/', api.DayViewSet.as_view({'get': 'list'}), name='day-list'),
    path('<juris:jurisdiction>/', api.DayViewSet.as_view({'get': 'retrieve_default'}), name='day-get-default'),
    path('<juris:jurisdiction>/ical/', api.ical, name='ical'),
    path('alexa/', orthodox_daily_view),
]

urlpatterns = format_suffix_patterns(urlpatterns)
