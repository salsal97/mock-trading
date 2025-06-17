from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register the ViewSets
router = DefaultRouter()
router.register(r'', views.MarketViewSet, basename='market')
router.register(r'spread-bids', views.SpreadBidViewSet, basename='spreadbid')
router.register(r'trades', views.TradeViewSet, basename='trade')

urlpatterns = [
    path('', include(router.urls)),
    path('<int:market_id>/settle/', views.settle_market, name='settle_market'),
    path('trade-history/', views.trade_history, name='trade_history'),
    path('auto-settle/', views.auto_settle_markets, name='auto_settle_markets'),
] 