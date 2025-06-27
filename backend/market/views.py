from rest_framework import status, viewsets, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from .models import Market, SpreadBid, Trade
from .serializers import (
    MarketSerializer, MarketCreateSerializer, MarketUpdateSerializer, MarketEditSerializer,
    SpreadBidSerializer, SpreadBidCreateSerializer,
    TradeSerializer, TradeCreateSerializer, TradeUpdateSerializer
)
from .permissions import IsAdminOrReadOnly
from .utils import create_success_response, create_error_response
import logging

logger = logging.getLogger(__name__)

def auto_activate_eligible_markets():
    """
    Helper function to auto-activate markets that are eligible.
    This implements lazy evaluation - markets are activated when accessed.
    
    Business rule: activate when there has been at least one bid from one user 
    and the spread bidding window is closed
    """
    # Get markets that have bids and bidding window is closed
    eligible_markets = Market.objects.filter(
        status='CREATED',
        spread_bidding_close_trading_open__lt=timezone.now(),
        final_spread_low__isnull=True,
        final_spread_high__isnull=True
    ).exclude(
        spread_bids__isnull=True  # Must have at least one bid
    ).distinct()
    
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
        # Rule 9: Only admins can create markets
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only administrators can create markets")
        
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
        """Manually activate a market (admin only) - allows admin override"""
        from django.utils import timezone
        
        market = self.get_object()
        
        # Allow admin override - check basic eligibility only
        if market.status != 'CREATED':
            return Response(
                {'error': 'Market must be in CREATED status to be activated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if market.final_spread_low is not None or market.final_spread_high is not None:
            return Response(
                {'error': 'Market has already been activated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Rule 1b: Admin can forcefully activate market using auto activate button
        # This is an admin override that bypasses the "at least one bid" requirement
        
        # Use the existing auto_activate_market method but bypass timing/bid check if needed
        original_close_time = market.spread_bidding_close_trading_open
        now = timezone.now()
        has_bids = market.spread_bids.exists()
        
        # Admin can always activate if bidding window is closed OR force early activation
        bidding_closed = now >= market.spread_bidding_close_trading_open
        admin_override = not bidding_closed or not has_bids
        
        try:
            if admin_override and not has_bids:
                # New rule: No default spread, must error out and ask for initial bid
                return Response({
                    'error': 'Cannot activate market without bids. Please ensure at least one spread bid is placed before activation, or have users place initial bids.',
                    'details': {
                        'bids_count': market.spread_bids.count(),
                        'requires_initial_bid': True,
                        'suggestion': 'Ask users to place spread bids first, then try activation again.'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Normal activation or admin override with bids
                if admin_override:
                    # Temporarily set bidding close to past time for admin override
                    market.spread_bidding_close_trading_open = now - timezone.timedelta(minutes=1)
                    market.save()
                
                result = market.auto_activate_market()
                
                if result['success']:
                    # Keep the original close time unless admin changed it intentionally
                    if admin_override:
                        market.spread_bidding_close_trading_open = now - timezone.timedelta(minutes=1)
                        market.save()
                    
                    serializer = MarketSerializer(market)
                    return Response({
                        'message': f"{result['reason']} (Admin Override)" if admin_override else result['reason'],
                        'details': result['details'],
                        'market': serializer.data
                    })
                else:
                    # Restore original time if activation failed
                    if admin_override:
                        market.spread_bidding_close_trading_open = original_close_time
                        market.save()
                    
                    return Response(
                        {'error': result['reason']},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        except Exception as e:
            # Restore original time if error occurred
            if admin_override:
                market.spread_bidding_close_trading_open = now - timezone.timedelta(minutes=1)
                market.save()
            
            return Response(
                {'error': f'Error during activation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        """
        Place a trade on a market (updated for market maker system)
        """
        try:
            market = self.get_object()
            
            if market.status != 'OPEN':
                return create_error_response("Market is not open for trading")
                
            if not market.market_maker:
                return create_error_response("Market does not have a market maker yet")
                
            if market.market_maker == request.user:
                return create_error_response("Market makers cannot trade on their own markets")
            
            position = request.data.get('position', '').upper()
            quantity = request.data.get('quantity', 1)
            
            if position not in ['LONG', 'SHORT']:
                return create_error_response("Position must be LONG or SHORT")
                
            try:
                quantity = int(quantity)
                if quantity <= 0:
                    return create_error_response("Quantity must be positive")
            except (ValueError, TypeError):
                return create_error_response("Invalid quantity")
            
            # Price is determined by market maker's spread
            if position == 'LONG':
                # Buying LONG (YES) - pay the higher price
                price = market.market_maker_spread_high
            else:
                # Buying SHORT (NO) - pay the lower price  
                price = market.market_maker_spread_low
                
            total_cost = Decimal(str(price)) * Decimal(str(quantity))
            
            # Check if user has sufficient balance
            if request.user.profile.balance < total_cost:
                return create_error_response("Insufficient balance")
            
            # Create the trade
            trade = Trade.objects.create(
                user=request.user,
                market=market,
                position=position,
                price=price,
                quantity=quantity
            )
            
            # Deduct cost from user balance
            request.user.profile.balance -= total_cost
            request.user.profile.save()
            
            return create_success_response(
                f"Trade placed successfully: {position} {quantity} units at ${price}",
                {
                    'trade_id': trade.id,
                    'position': position,
                    'price': float(price),
                    'quantity': quantity,
                    'total_cost': float(total_cost),
                    'remaining_balance': float(request.user.profile.balance)
                }
            )
            
        except Exception as e:
            return create_error_response(f"Error placing trade: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
@permission_classes([IsAuthenticated, IsAdminUser])
def close_trading(request, market_id):
    """
    Manually close trading on a market (admin only)
    """
    try:
        market = get_object_or_404(Market, id=market_id)
        
        if market.status != 'OPEN':
            return create_error_response("Market is not open for trading", status_code=status.HTTP_400_BAD_REQUEST)
        
        market.status = 'CLOSED'
        market.save()
        
        return create_success_response(
            "Market trading closed successfully", 
            {
                'market_id': market.id,
                'status': market.status,
                'closed_at': timezone.now().isoformat(),
                'total_trades': market.trades.count()
            }
        )
        
    except Exception as e:
        return create_error_response(f"Error closing market: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def set_settlement_price(request, market_id):
    """
    Set settlement price for a closed market (admin only)
    """
    try:
        market = get_object_or_404(Market, id=market_id)
        
        if market.status != 'CLOSED':
            return create_error_response("Market must be CLOSED before setting settlement price", status_code=status.HTTP_400_BAD_REQUEST)
        
        if market.settlement_price is not None:
            return create_error_response("Settlement price has already been set", status_code=status.HTTP_400_BAD_REQUEST)
        
        price = request.data.get('price')
        if price is None:
            return create_error_response("Settlement price is required", status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            price = Decimal(str(price))
        except (ValueError, TypeError):
            return create_error_response("Invalid price format", status_code=status.HTTP_400_BAD_REQUEST)
        
        # Validate price range
        if not (Decimal('0.01') <= price <= Decimal('999999.99')):
            return create_error_response("Settlement price must be between 0.01 and 999999.99", status_code=status.HTTP_400_BAD_REQUEST)
        
        final_price = market.set_settlement_price(price)
        
        return create_success_response(
            "Settlement price set successfully",
            {
                'market_id': market.id,
                'settlement_price': float(final_price),
                'can_preview': True,
                'total_trades': market.trades.count()
            }
        )
        
    except ValidationError as e:
        return create_error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return create_error_response(f"Error setting settlement price: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def settlement_preview(request, market_id):
    """
    Get settlement preview showing all trade impacts (admin only)
    """
    try:
        market = get_object_or_404(Market, id=market_id)
        
        if market.settlement_price is None:
            return create_error_response("Settlement price must be set before preview", status_code=status.HTTP_400_BAD_REQUEST)
        
        settlement_data = market.calculate_settlement_preview()
        
        return create_success_response(
            "Settlement preview calculated successfully",
            settlement_data
        )
        
    except ValidationError as e:
        return create_error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return create_error_response(f"Error calculating settlement preview: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def execute_settlement(request, market_id):
    """
    Execute final settlement and update all user balances (admin only)
    """
    try:
        market = get_object_or_404(Market, id=market_id)
        
        confirmed = request.data.get('confirmed', False)
        if not confirmed:
            return create_error_response("Admin confirmation required - set 'confirmed': true", status_code=status.HTTP_400_BAD_REQUEST)
        
        result = market.execute_settlement(confirmed_by_admin=True)
        
        if result['success']:
            return create_success_response(
                result['message'],
                result
            )
        else:
            return create_error_response(result['message'], status_code=status.HTTP_400_BAD_REQUEST)
        
    except ValidationError as e:
        return create_error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return create_error_response(f"Error executing settlement: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def reopen_trading(request, market_id):
    """
    Reopen trading for a closed market with new close time (admin only)
    """
    try:
        market = get_object_or_404(Market, id=market_id)
        
        if not market.can_be_reopened:
            return create_error_response("Market cannot be reopened - either not closed or settlement already started", status_code=status.HTTP_400_BAD_REQUEST)
        
        new_close_time_str = request.data.get('new_trading_close')
        if not new_close_time_str:
            return create_error_response("New trading close time is required", status_code=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            new_close_time = datetime.fromisoformat(new_close_time_str.replace('Z', '+00:00'))
            if new_close_time.tzinfo is None:
                new_close_time = timezone.make_aware(new_close_time)
        except ValueError:
            return create_error_response("Invalid datetime format. Use ISO format", status_code=status.HTTP_400_BAD_REQUEST)
        
        market.reopen_trading(new_close_time)
        
        return create_success_response(
            "Market reopened for trading successfully",
            {
                'market_id': market.id,
                'status': market.status,
                'new_trading_close': market.trading_close.isoformat(),
                'reopened_at': timezone.now().isoformat()
            }
        )
        
    except ValidationError as e:
        return create_error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return create_error_response(f"Error reopening market: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def settle_market(request, market_id):
    """
    Legacy settlement endpoint - now redirects to new settlement flow
    """
    try:
        market = get_object_or_404(Market, id=market_id)
        
        # Legacy endpoint - close market if open
        if market.status == 'OPEN':
            market.status = 'CLOSED'
            market.save()
        
        return create_success_response(
            "Market closed. Use new settlement endpoints: set_settlement_price -> settlement_preview -> execute_settlement",
            {
                'market_id': market.id,
                'status': market.status,
                'next_steps': {
                    'set_price': f'/api/market/{market_id}/set_settlement_price/',
                    'preview': f'/api/market/{market_id}/settlement_preview/',
                    'execute': f'/api/market/{market_id}/execute_settlement/'
                }
            }
        )
        
    except Exception as e:
        return create_error_response(f"Error in legacy settlement: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def anonymous_trade_history(request):
    """
    Get anonymous trade history for all settled markets (users can see all trades but usernames are hidden)
    """
    try:
        # Only show trades from settled markets
        trades = Trade.objects.filter(
            market__status='SETTLED'
        ).select_related('market', 'user').order_by('-trade_time')
        
        trade_data = []
        for trade in trades:
            trade_info = {
                'id': trade.id,
                'market': {
                    'id': trade.market.id,
                    'premise': trade.market.premise,
                    'settlement_price': float(trade.market.settlement_price) if trade.market.settlement_price else None,
                    'settled_at': trade.market.settled_at.isoformat() if trade.market.settled_at else None
                },
                'position': trade.position,
                'price': float(trade.price),
                'quantity': trade.quantity,
                'trade_time': trade.trade_time.isoformat(),
                'profit_loss': float(trade.profit_loss) if trade.profit_loss else 0,
                'won': (
                    (trade.position == 'LONG' and trade.profit_loss > 0) or
                    (trade.position == 'SHORT' and trade.profit_loss > 0)
                ) if trade.profit_loss is not None else None,
                # Username is hidden for privacy
                'trader': f"User_{trade.user.id}" if not request.user.is_staff else trade.user.username
            }
            trade_data.append(trade_info)
        
        return create_success_response(
            "Anonymous trade history retrieved successfully",
            {
                'trades': trade_data,
                'total_trades': len(trade_data),
                'note': 'Only settled markets shown. Usernames anonymized for privacy.'
            }
        )
        
    except Exception as e:
        return create_error_response(f"Error retrieving anonymous trade history: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auto_settle_markets(request):
    """
    Check and auto-settle markets that have reached their trading_close time (admin only)
    """
    try:
        if not request.user.is_staff:
            return create_error_response("Admin access required", status_code=status.HTTP_403_FORBIDDEN)
            
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
        return create_error_response(f"Error in auto-settlement: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_market_maker(request, market_id):
    """
    Set a user as market maker for a market with their spread
    """
    try:
        market = get_object_or_404(Market, id=market_id)
        
        if market.status != 'OPEN':
            return create_error_response("Market is not open for trading")
            
        if market.market_maker:
            return create_error_response("Market already has a market maker")
            
        spread_low = request.data.get('spread_low')
        spread_high = request.data.get('spread_high')
        
        if spread_low is None or spread_high is None:
            return create_error_response("Both spread_low and spread_high are required")
            
        spread_low = float(spread_low)
        spread_high = float(spread_high)
        
        if spread_low >= spread_high:
            return create_error_response("Spread high must be greater than spread low")
            
        if spread_low < 0 or spread_high > 100:
            return create_error_response("Spread values must be between 0 and 100")
            
        # Set the user as market maker
        market.market_maker = request.user
        market.market_maker_spread_low = spread_low
        market.market_maker_spread_high = spread_high
        market.save()
        
        return create_success_response(
            f"Successfully set as market maker with spread: ${spread_low} - ${spread_high}",
            {
                'market_id': market.id,
                'market_maker': request.user.username,
                'spread_low': spread_low,
                'spread_high': spread_high
            }
        )
        
    except ValueError:
        return create_error_response("Invalid spread values")
    except Exception as e:
        return create_error_response(f"Error setting market maker: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_positions(request):
    """
    Get user's current active positions (trades on open markets)
    """
    try:
        # Get user's trades on open markets
        active_trades = Trade.objects.filter(
            user=request.user,
            market__status='OPEN'
        ).select_related('market').order_by('-trade_time')
        
        positions_data = []
        for trade in active_trades:
            market = trade.market
            position_info = {
                'id': trade.id,
                'market_id': market.id,
                'market_premise': market.premise,
                'market_status': market.status,
                'market': {
                    'id': market.id,
                    'premise': market.premise,
                    'status': market.status,
                    'trading_close': market.trading_close.isoformat(),
                    'final_spread_low': market.final_spread_low,
                    'final_spread_high': market.final_spread_high
                },
                'position': trade.position,
                'price': float(trade.price),
                'quantity': trade.quantity,
                'total_quantity': trade.quantity,  # Frontend expects this
                'average_price': float(trade.price),  # Frontend expects this
                'total_cost': float(trade.price * trade.quantity),
                'current_value': float(
                    market.market_maker_spread_high if trade.position == 'LONG' 
                    else market.market_maker_spread_low
                ) * trade.quantity if market.market_maker_spread_high else float(trade.price * trade.quantity),
                'unrealized_pnl': float(
                    (float(market.market_maker_spread_high) - float(trade.price)) * trade.quantity 
                    if trade.position == 'LONG' 
                    else (float(trade.price) - float(market.market_maker_spread_low)) * trade.quantity
                ) if market.market_maker_spread_high and market.market_maker_spread_low else 0.0,
                'trade_time': trade.trade_time.isoformat(),
                'is_settled': trade.is_settled
            }
            
            # Add settlement info if settled
            if trade.is_settled:
                position_info.update({
                    'settlement_amount': float(trade.settlement_amount or 0),
                    'profit_loss': float(trade.profit_loss or 0),
                    'settled_at': trade.settled_at.isoformat() if trade.settled_at else None
                })
            
            positions_data.append(position_info)
        
        total_unrealized_pnl = sum([pos['unrealized_pnl'] for pos in positions_data])
        
        return create_success_response(
            "Positions retrieved successfully",
            {
                'positions': positions_data,
                'total_positions': len(positions_data),
                'total_unrealized_pnl': total_unrealized_pnl
            }
        )
        
    except Exception as e:
        return create_error_response(f"Error retrieving positions: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trade_history(request):
    """
    Get user's personal trade history with settlement information
    """
    try:
        trades = Trade.objects.filter(user=request.user).select_related('market').order_by('-trade_time')
        
        trade_data = []
        total_profit_loss = Decimal('0.00')
        
        for trade in trades:
            trade_info = {
                'id': trade.id,
                'market': {
                    'id': trade.market.id,
                    'premise': trade.market.premise,
                    'status': trade.market.status,
                    'settlement_price': float(trade.market.settlement_price) if trade.market.settlement_price else None,
                    'settled_at': trade.market.settled_at.isoformat() if trade.market.settled_at else None
                },
                'position': trade.position,
                'price': float(trade.price),
                'quantity': trade.quantity,
                'total_cost': float(trade.price * trade.quantity),
                'trade_time': trade.trade_time.isoformat(),
                'is_settled': trade.is_settled
            }
            
            if trade.is_settled and trade.profit_loss is not None:
                trade_info.update({
                    'settlement_amount': float(trade.settlement_amount or 0),
                    'profit_loss': float(trade.profit_loss),
                    'settled_at': trade.settled_at.isoformat() if trade.settled_at else None,
                    'won': trade.profit_loss > 0
                })
                total_profit_loss += trade.profit_loss
            
            trade_data.append(trade_info)
        
        return create_success_response(
            "Trade history retrieved successfully",
            {
                'trades': trade_data,
                'total_trades': len(trade_data),
                'settled_trades': len([t for t in trade_data if t['is_settled']]),
                'total_profit_loss': float(total_profit_loss)
            }
        )
        
    except Exception as e:
        return create_error_response(f"Error retrieving trade history: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
