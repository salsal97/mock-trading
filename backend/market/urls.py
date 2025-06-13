from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register the MarketViewSet
router = DefaultRouter()
router.register(r'', views.MarketViewSet, basename='market')

urlpatterns = [
    path('', include(router.urls)),
] 