from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Market, SpreadBid, Trade
from .serializers import (
    MarketSerializer, MarketCreateSerializer, MarketUpdateSerializer, MarketEditSerializer,
    SpreadBidSerializer, SpreadBidCreateSerializer,
    TradeSerializer, TradeCreateSerializer, TradeUpdateSerializer
)
from .permissions import IsAdminOrReadOnly
import logging

logger = logging.getLogger(__name__)

def auto_activate_eligible_markets():
    """
    Helper function to auto-activate markets that are eligible.
    This implements lazy evaluation - markets are activated when accessed.
    """
    eligible_markets = Market.objects.filter(
        status='CREATED',
        spread_bidding_close__lt=timezone.now(),
        final_spread_low__isnull=True,
        final_spread_high__isnull=True
    )
    
    activated_count = 0
    for market in eligible_markets:
        result = market.auto_activate_market()
        if result['success']:
            activated_count += 1
            logger.info(f"Auto-activated market {market.id}: {result['reason']}")
        else:
            logger.warning(f"Failed to auto-activate market {market.id}: {result['reason']}")
    
    if activated_count > 0:
        logger.info(f"Lazy evaluation: auto-activated {activated_count} markets")
    
    return activated_count

class MarketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing markets.
    - GET operations: Available to all authenticated users
    - POST/PUT/PATCH/DELETE operations: Admin users only
    """
    queryset = Market.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return MarketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MarketUpdateSerializer
        return MarketSerializer
    
    def get_queryset(self):
        """Filter markets based on query parameters"""
        # Auto-activate eligible markets (lazy evaluation)
        auto_activate_eligible_markets()
        
        queryset = Market.objects.all()
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by active trading
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(status='OPEN')
        
        return queryset.order_by('-created_at')
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to auto-activate market if eligible"""
        # Auto-activate eligible markets before retrieving
        auto_activate_eligible_markets()
        return super().retrieve(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Set the created_by field to the current user when creating a market"""
        serializer.save(created_by=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Override create to return full market data after creation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return full market data using MarketSerializer
        market = serializer.instance
        response_serializer = MarketSerializer(market)
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add business logic"""
        market = self.get_object()
        
        # Only allow deletion of markets that haven't started trading
        if market.status not in ['CREATED']:
            return Response(
                {'error': 'Cannot delete markets that have started trading'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def settle(self, request, pk=None):
        """Settle a market with outcome (admin only)"""
        market = self.get_object()
        
        if not market.can_be_settled:
            return Response(
                {'error': 'Market cannot be settled at this time'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        outcome = request.data.get('outcome')
        if outcome is None:
            return Response(
                {'error': 'Outcome is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            outcome = int(outcome)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Outcome must be an integer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        market.status = 'SETTLED'
        market.outcome = outcome
        market.save()
        
        serializer = MarketSerializer(market)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdminUser])
    def stats(self, request):
        """Get market statistics for admin dashboard"""
        # Auto-activate eligible markets before generating stats
        auto_activate_eligible_markets()
        
        total_markets = Market.objects.count()
        markets_by_status = {}
        
        for status_choice in Market.STATUS_CHOICES:
            status_key = status_choice[0]
            count = Market.objects.filter(status=status_key).count()
            markets_by_status[status_key] = count
        
        active_trading = Market.objects.filter(status='OPEN').count()
        
        stats = {
            'total_markets': total_markets,
            'markets_by_status': markets_by_status,
            'active_trading': active_trading,
            'recent_markets': MarketSerializer(
                Market.objects.order_by('-created_at')[:5], 
                many=True
            ).data
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def spread_bids(self, request, pk=None):
        """Get all spread bids for a market"""
        market = self.get_object()
        bids = market.spread_bids.all().order_by('bid_time')
        serializer = SpreadBidSerializer(bids, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def place_spread_bid(self, request, pk=None):
        """Place a spread bid on a market"""
        market = self.get_object()
        
        # Create serializer with market and user context
        serializer = SpreadBidCreateSerializer(
            data={**request.data, 'market': market.id},
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Save the bid with the authenticated user
            spread_bid = serializer.save(user=request.user)
            
            # Return the created bid data
            response_serializer = SpreadBidSerializer(spread_bid)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdminUser])
    def manual_activate(self, request, pk=None):
        """Manually activate a market (admin only)"""
        market = self.get_object()
        
        if not market.should_auto_activate:
            return Response(
                {'error': 'Market is not eligible for activation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = market.auto_activate_market()
        
        if result['success']:
            serializer = MarketSerializer(market)
            return Response({
                'message': result['reason'],
                'details': result['details'],
                'market': serializer.data
            })
        else:
            return Response(
                {'error': result['reason']},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['put', 'patch'], permission_classes=[IsAuthenticated, IsAdminUser])
    def edit(self, request, pk=None):
        """Comprehensive market editing for admins"""
        market = self.get_object()
        
        # Use partial update for PATCH, full update for PUT
        partial = request.method == 'PATCH'
        
        serializer = MarketEditSerializer(
            market, 
            data=request.data, 
            partial=partial
        )
        
        if serializer.is_valid():
            serializer.save()
            
            # Return full market data
            response_serializer = MarketSerializer(market)
            return Response({
                'message': 'Market updated successfully',
                'market': response_serializer.data
            })
        else:
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def place_trade(self, request, pk=None):
        """Place a trade on a market"""
        market = self.get_object()
        
        # Check if user already has a trade on this market
        existing_trade = market.get_user_trade(request.user)
        
        if existing_trade:
            # Update existing trade
            serializer = TradeUpdateSerializer(
                existing_trade,
                data=request.data,
                context={'request': request}
            )
        else:
            # Create new trade
            serializer = TradeCreateSerializer(
                data={**request.data, 'market': market.id},
                context={'request': request}
            )
        
        if serializer.is_valid():
            trade = serializer.save()
            
            # Return the trade data
            response_serializer = TradeSerializer(trade)
            return Response({
                'message': 'Trade placed successfully' if not existing_trade else 'Trade updated successfully',
                'trade': response_serializer.data
            })
        else:
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def trades(self, request, pk=None):
        """Get all trades for a market"""
        market = self.get_object()
        
        # Filter by position if specified
        position_filter = request.query_params.get('position')
        trades = market.trades.all()
        
        if position_filter and position_filter.upper() in ['LONG', 'SHORT']:
            trades = trades.filter(position=position_filter.upper())
        
        serializer = TradeSerializer(trades, many=True)
        return Response({
            'trades': serializer.data,
            'long_count': market.long_trades_count,
            'short_count': market.short_trades_count,
            'total_count': market.total_trades_count
        })

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def cancel_trade(self, request, pk=None):
        """Cancel user's trade on a market (only if trading is still open)"""
        market = self.get_object()
        
        # Check if market is still open for trading
        if not market.is_trading_active:
            return Response(
                {'error': 'Cannot cancel trade - market is closed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user's trade
        trade = market.get_user_trade(request.user)
        if not trade:
            return Response(
                {'error': 'No trade found for this user on this market'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Delete the trade
        trade.delete()
        
        return Response({
            'message': 'Trade cancelled successfully'
        })

class SpreadBidViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing spread bids.
    Only read operations are allowed - bids are created through MarketViewSet.
    """
    queryset = SpreadBid.objects.all()
    serializer_class = SpreadBidSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter spread bids based on query parameters"""
        queryset = SpreadBid.objects.all()
        
        # Filter by market if provided
        market_id = self.request.query_params.get('market')
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        
        # Filter by user if provided (for user's own bids)
        user_only = self.request.query_params.get('user_only')
        if user_only and user_only.lower() == 'true':
            queryset = queryset.filter(user=self.request.user)
        
        return queryset.order_by('-bid_time')

class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing trades.
    Trade creation/updates are handled through MarketViewSet.
    """
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter trades based on query parameters and user permissions"""
        queryset = Trade.objects.all()
        
        # Regular users can only see their own trades
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Filter by market if provided
        market_id = self.request.query_params.get('market')
        if market_id:
            queryset = queryset.filter(market_id=market_id)
        
        # Filter by position if provided
        position = self.request.query_params.get('position')
        if position and position.upper() in ['LONG', 'SHORT']:
            queryset = queryset.filter(position=position.upper())
        
        return queryset.order_by('-trade_time')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def settle_market(request, market_id):
    """
    Manually settle a market (admin only)
    """
    try:
        if not request.user.is_staff:
            return create_error_response("Admin access required", 403)
            
        market = get_object_or_404(Market, id=market_id)
        
        outcome = request.data.get('outcome')  # True for YES/LONG wins, False for NO/SHORT wins
        settlement_price = request.data.get('settlement_price')
        
        if outcome is None:
            return create_error_response("Outcome is required (true for YES, false for NO)")
            
        success, message = market.settle_market(outcome, settlement_price)
        
        if success:
            return create_success_response(
                message,
                {
                    'market_id': market.id,
                    'final_outcome': market.final_outcome,
                    'settlement_price': float(market.settlement_price),
                    'settled_at': market.settled_at.isoformat(),
                    'total_trades_settled': market.trade_set.filter(is_settled=True).count()
                }
            )
        else:
            return create_error_response(message)
            
    except Exception as e:
        return create_error_response(f"Error settling market: {str(e)}", 500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trade_history(request):
    """
    Get user's trade history with settlement information
    """
    try:
        trades = Trade.objects.filter(user=request.user).select_related('market').order_by('-created_at')
        
        trade_data = []
        for trade in trades:
            trade_info = {
                'id': trade.id,
                'market': {
                    'id': trade.market.id,
                    'premise': trade.market.premise,
                    'status': trade.market.status
                },
                'position': trade.position,
                'price': float(trade.price),
                'quantity': trade.quantity,
                'total_cost': float(trade.price * trade.quantity),
                'created_at': trade.created_at.isoformat(),
                'is_settled': trade.is_settled
            }
            
            if trade.is_settled:
                trade_info.update({
                    'settlement_amount': float(trade.settlement_amount or 0),
                    'profit_loss': float(trade.profit_loss or 0),
                    'settled_at': trade.settled_at.isoformat() if trade.settled_at else None,
                    'market_outcome': trade.market.final_outcome,
                    'won': (
                        (trade.position == 'LONG' and trade.market.final_outcome) or
                        (trade.position == 'SHORT' and not trade.market.final_outcome)
                    ) if trade.market.final_outcome is not None else None
                })
            
            trade_data.append(trade_info)
        
        return create_success_response(
            "Trade history retrieved successfully",
            {
                'trades': trade_data,
                'total_trades': len(trade_data),
                'settled_trades': len([t for t in trade_data if t['is_settled']]),
                'total_profit_loss': sum([float(t.profit_loss or 0) for t in trades if t.is_settled])
            }
        )
        
    except Exception as e:
        return create_error_response(f"Error retrieving trade history: {str(e)}", 500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_settle_markets(request):
    """
    Check and auto-settle markets that have reached their trading_close time (admin only)
    """
    try:
        if not request.user.is_staff:
            return create_error_response("Admin access required", 403)
            
        markets_to_close = Market.objects.filter(
            status='OPEN',
            trading_close__lte=timezone.now()
        )
        
        closed_count = 0
        for market in markets_to_close:
            if market.auto_settle_if_time():
                closed_count += 1
                
        return create_success_response(
            f"Auto-settlement check completed. {closed_count} markets moved to CLOSED status",
            {
                'markets_closed': closed_count,
                'markets_checked': markets_to_close.count()
            }
        )
        
    except Exception as e:
        return create_error_response(f"Error in auto-settlement: {str(e)}", 500)
