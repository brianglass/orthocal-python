from django.urls import path

from . import views

urlpatterns = [
    path('saints/', views.search_view, name='saint-search'),
    path('saints/<int:pk>/', views.saint_detail_view, name='saint-detail'),
]
