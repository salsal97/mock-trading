from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register the ViewSets
router = DefaultRouter()
router.register(r'', views.MarketViewSet, basename='market')
router.register(r'spread-bids', views.SpreadBidViewSet, basename='spreadbid')
router.register(r'trades', views.TradeViewSet, basename='trade')

urlpatterns = [
    # Function-based views must come before router URLs to avoid conflicts
    path('trade-history/', views.trade_history, name='trade_history'),
    path('anonymous-trade-history/', views.anonymous_trade_history, name='anonymous_trade_history'),
    path('positions/', views.user_positions, name='user_positions'),
    path('auto-settle/', views.auto_settle_markets, name='auto_settle_markets'),
    
    # Legacy settlement endpoint (for backward compatibility)
    path('<int:market_id>/settle/', views.settle_market, name='settle_market'),
    
    # New settlement workflow endpoints
    path('<int:market_id>/close-trading/', views.close_trading, name='close_trading'),
    path('<int:market_id>/set-settlement-price/', views.set_settlement_price, name='set_settlement_price'),
    path('<int:market_id>/settlement-preview/', views.settlement_preview, name='settlement_preview'),
    path('<int:market_id>/execute-settlement/', views.execute_settlement, name='execute_settlement'),
    path('<int:market_id>/reopen-trading/', views.reopen_trading, name='reopen_trading'),
    
    path('<int:market_id>/set-market-maker/', views.set_market_maker, name='set_market_maker'),
    # Router URLs come last
    path('', include(router.urls)),
] 