from django.urls import path
from django_ask_sdk.skill_adapter import SkillAdapter
from rest_framework.urlpatterns import format_suffix_patterns

from . import skills

orthodox_daily_view = SkillAdapter.as_view(skill=skills.orthodox_daily_skill)

urlpatterns = [
    path('echo/', orthodox_daily_view),
]

urlpatterns = format_suffix_patterns(urlpatterns)
