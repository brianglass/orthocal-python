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
from django.urls import include, path, register_converter
from django.views.generic import TemplateView

class JurisdictionConverter:
    regex = '(oca|rocor)'

    def to_python(self, value):
        return value

    def to_url(self, value):
        return value

register_converter(JurisdictionConverter, 'juris')

urlpatterns = [
    path('alexa/', TemplateView.as_view(template_name='alexa.html'), name='alexa'),
    path('api/', TemplateView.as_view(template_name='api.html'), name='api'),
    path('ical/', TemplateView.as_view(template_name='ical.html'), name='icalendar'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('api/', include('calendarium.api_urls')),
    path('', include('calendarium.urls')),
]
