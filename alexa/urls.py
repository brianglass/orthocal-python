from django.urls import path
from django.views.decorators.cache import never_cache

from . import views

urlpatterns = [
    path('echo/', never_cache(views.orthodox_daily_view)),
]
