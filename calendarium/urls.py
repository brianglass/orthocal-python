from django.urls import path
from django.views.decorators.vary import vary_on_cookie
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from . import views

urlpatterns = [
    path('readings/<cal:cal>/<year:year>/<month:month>/<day:day>/', views.readings_view, name='readings'),
    path('calendar/<cal:cal>/<year:year>/<month:month>/<day:day>/', RedirectView.as_view(permanent=True, pattern_name='readings')),
    path('calendar/<cal:cal>/<year:year>/<month:month>/', views.calendar_view, name='calendar'),
    path('calendar-embed/<cal:cal>/<year:year>/<month:month>/', views.calendar_embed_view, name='calendar-embed'),
    path('calendar-embed/', views.calendar_embed_view, name='calendar-embed-default'),
    path('calendar/<cal:cal>/', views.calendar_view, name='calendar-calopt'),
    path('calendar/', vary_on_cookie(views.calendar_view), name='calendar-default'),
    path('lectionary/', views.lectionary, name='lectionary'),
    path('', vary_on_cookie(views.readings_view), name='index'),
]
