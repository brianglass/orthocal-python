from django.urls import path
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from . import views

urlpatterns = [
    path('readings/<cal:cal>/<int:year>/<int:month>/<int:day>/', views.readings_view, name='readings'),
    path('calendar/<cal:cal>/<int:year>/<int:month>/<int:day>/', RedirectView.as_view(permanent=True, pattern_name='readings')),
    path('calendar/<cal:cal>/<int:year>/<int:month>/', views.calendar_view, name='calendar'),
    path('calendar-embed/<cal:cal>/<int:year>/<int:month>/', views.calendar_embed_view, name='calendar'),
    path('calendar-embed/', views.calendar_embed_view, name='calendar'),
    path('calendar/<cal:cal>/', views.calendar_view, name='calendar-calopt'),
    path('calendar/', views.calendar_view, name='calendar-default'),
    path('', views.readings_view, name='index'),
]
