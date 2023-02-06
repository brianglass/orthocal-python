"""orthocal URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, register_converter, reverse
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from . import converters
from . import sitemaps

register_converter(converters.CalendarConverter, 'cal')
register_converter(converters.YearConverter, 'year')
register_converter(converters.MonthConverter, 'month')
register_converter(converters.DayConverter, 'day')

sitemaps = {
        'static': sitemaps.StaticViewSitemap,
        'calendar': sitemaps.CalendarSitemap,
        'calendar-julian': sitemaps.CalendarJulianSitemap,
        'readings': sitemaps.ReadingsSitemap,
        'readings-julian': sitemaps.ReadingsJulianSitemap,
}

urlpatterns = [
    path('alexa/', TemplateView.as_view(template_name='alexa.html'), name='alexa'),
    path('api/', TemplateView.as_view(template_name='api.html'), name='api'),
    path('ical/', RedirectView.as_view(permanent=True, pattern_name='feeds')),
    path('feeds/', TemplateView.as_view(template_name='feeds.html'), name='feeds'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('api/', include('calendarium.api_urls')),
    path('', include('alexa.urls')),
    path('', include('calendarium.urls')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
]
