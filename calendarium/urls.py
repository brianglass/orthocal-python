from django.urls import path
from django.views.generic import TemplateView
from rest_framework.urlpatterns import format_suffix_patterns

from . import views

urlpatterns = [
    path('calendar/<juris:jurisdiction>/<int:year>/<int:month>/<int:day>/', views.readings, name='calendar-day'),
    path('calendar/<juris:jurisdiction>/<int:year>/<int:month>/', views.calendar_view, name='calendar-month'),
    path('calendar/', views.calendar_view, name='calendar-month-default'),
    path('', views.readings, name='index'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
