from django.urls import path

from . import views

urlpatterns = [
    path('saints/', views.search_view, name='saint-search'),
    path('saints/<slug:slug>/', views.saint_detail_view, name='saint-detail'),
]
