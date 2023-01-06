from django.urls import path
from django.views.generic import TemplateView
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('calendar/<juris:jurisdiction>/<int:year>/<int:month>/<int:day>/', views.readings, name='calendar'),
    path('', views.readings, name='index'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
