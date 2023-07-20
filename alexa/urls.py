from django.urls import path
from .skill_adapter import SkillAdapter

from . import skills

orthodox_daily_view = SkillAdapter.as_view(skill=skills.orthodox_daily_skill)

urlpatterns = [
    path('echo/', orthodox_daily_view),
]
