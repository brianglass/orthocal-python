from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path('readings/<cal:cal>/<int:year>/<int:month>/<int:day>/', views.readings_view, name='readings'),
    path('calendar/<cal:cal>/<int:year>/<int:month>/', views.calendar_view, name='calendar-month'),
    path('calendar/', views.calendar_view, name='calendar-month-default'),
    path('', views.readings_view, name='index'),
]
