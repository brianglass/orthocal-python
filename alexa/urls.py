from django.urls import path
from django_ask_sdk.skill_adapter import SkillAdapter

from . import skills

orthodox_daily_view = SkillAdapter.as_view(skill=skills.orthodox_daily_skill)

urlpatterns = [
    path('echo/', orthodox_daily_view),
]
