from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register the ViewSets
router = DefaultRouter()
router.register(r'', views.MarketViewSet, basename='market')
router.register(r'spread-bids', views.SpreadBidViewSet, basename='spreadbid')

urlpatterns = [
    path('', include(router.urls)),
] 