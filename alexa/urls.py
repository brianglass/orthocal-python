from django.urls import path
from django.views.decorators.cache import never_cache

from .skill_adapter import SkillAdapter
from . import skills

orthodox_daily_view = SkillAdapter.as_view(skill=skills.orthodox_daily_skill)

urlpatterns = [
    path('echo/', never_cache(orthodox_daily_view)),
]
