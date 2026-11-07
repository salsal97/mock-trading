from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create a router and register the ViewSets
router = DefaultRouter()
router.register(r'', views.MarketViewSet, basename='market')

urlpatterns = [
    # Function-based views must come before router URLs to avoid conflicts
    path('<int:market_id>/settled-trades/', views.settled_market_trades, name='settled_market_trades'),
    
    # Settlement workflow
    path('<int:market_id>/close-trading/', views.close_trading, name='close_trading'),
    path('<int:market_id>/set-settlement-price/', views.set_settlement_price, name='set_settlement_price'),
    path('<int:market_id>/settlement-preview/', views.settlement_preview, name='settlement_preview'),
    path('<int:market_id>/execute-settlement/', views.execute_settlement, name='execute_settlement'),
    path('<int:market_id>/reopen-trading/', views.reopen_trading, name='reopen_trading'),
    
    # Router URLs come last
    path('', include(router.urls)),
] 