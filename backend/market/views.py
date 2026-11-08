from rest_framework import status, viewsets, permissions, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal, InvalidOperation
from .models import Market, Trade
from .settlement import calculate_settlement_preview, execute_settlement as settle_market
from .serializers import (
    MarketSerializer, MarketCreateSerializer, MarketEditSerializer,
    SpreadBidSerializer, SpreadBidCreateSerializer,
    TradeSerializer
)
from .utils import create_success_response, create_error_response

from .lifecycle import maintain_markets

class MarketViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Market browsing, bidding, and market-specific administration."""
    queryset = Market.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return MarketCreateSerializer
        return MarketSerializer

    def get_queryset(self):
        """Filter markets based on query parameters"""
        maintain_markets()

        queryset = Market.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(status='OPEN')

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """Set the created_by field to the current user when creating a market"""
        serializer.save(created_by=self.request.user, initial_spread=1)

    def create(self, request, *args, **kwargs):
        """Override create to return full market data after creation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        market = serializer.instance
        response_serializer = MarketSerializer(market)
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        market = get_object_or_404(Market.objects.select_for_update(), pk=kwargs['pk'])
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)
        if market.status != 'CREATED' or market.spread_bids.exists():
            return Response({'error': 'Only an unused market can be deleted'}, status=400)
        market.delete()
        return Response(status=204)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def place_spread_bid(self, request, pk=None):
        """Place a spread bid on a market"""
        market = get_object_or_404(Market.objects.select_for_update(), pk=pk)
        serializer = SpreadBidCreateSerializer(
            data={**request.data, 'market': market.id},
            context={'request': request}
        )

        if serializer.is_valid():
            spread_bid = serializer.save(user=request.user)
            response_serializer = SpreadBidSerializer(spread_bid)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def manual_activate(self, request, pk=None):
        market = get_object_or_404(Market.objects.select_for_update(), pk=pk)
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)
        now = timezone.now()
        if market.status != 'CREATED' or now < market.spread_bidding_open or now >= market.trading_close:
            return Response({'error': 'Market is not eligible for activation'}, status=400)
        bid = market.best_spread_bid
        if not bid:
            return Response({'error': 'At least one quote is required'}, status=400)
        market.spread_bidding_close_trading_open = min(market.spread_bidding_close_trading_open, now)
        market.final_spread_low, market.final_spread_high = bid.spread_low, bid.spread_high
        market.market_maker = bid.user
        market.market_maker_spread_low, market.market_maker_spread_high = bid.spread_low, bid.spread_high
        market.status = 'OPEN'
        market.save()
        return Response({'message': 'Market activated', 'market': MarketSerializer(market, context={'request': request}).data})

    @action(detail=True, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    @transaction.atomic
    def edit(self, request, pk=None):
        """Comprehensive market editing for admins"""
        market = get_object_or_404(Market.objects.select_for_update(), pk=pk)
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)

        allowed = {'premise', 'unit_value', 'spread_bidding_open', 'spread_bidding_close_trading_open', 'trading_close'}
        if market.status == 'SETTLED' or set(request.data) - allowed:
            return Response({'error': 'Use lifecycle actions for status and outcome'}, status=400)
        partial = request.method == 'PATCH'

        serializer = MarketEditSerializer(
            market,
            data=request.data,
            partial=partial
        )

        if serializer.is_valid():
            serializer.save()
            if 'unit_value' in request.data:
                market.settlement_preview_calculated = False
                market.save()
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
        with transaction.atomic():
            market = get_object_or_404(Market.objects.select_for_update(), pk=pk)
            allowed, reason = market.can_user_trade(request.user)
            if not allowed:
                return Response({'error': reason}, status=400)
            position = request.data.get('position', '')
            if not isinstance(position, str):
                return Response({'error': 'Choose BUY or SELL'}, status=400)
            position = position.upper()
            if position not in ('BUY', 'SELL'):
                return Response({'error': 'Choose BUY or SELL'}, status=400)
            if 'quantity' in request.data:
                return Response({'error': 'Positions do not have quantities'}, status=400)
            position = {'BUY': 'LONG', 'SELL': 'SHORT'}[position]
            price = market.market_maker_spread_high if position == 'LONG' else market.market_maker_spread_low
            trade, _ = Trade.objects.update_or_create(
                market=market, user=request.user,
                defaults={'position': position, 'price': float(price), 'quantity': 1})
            return Response({'message': 'Position saved', 'trade_id': trade.id, 'position': 'BUY' if position == 'LONG' else 'SELL', 'price': price})

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def trades(self, request, pk=None):
        """Get all trades for a market"""
        market = self.get_object()
        position_filter = request.query_params.get('position')
        trades = market.trades.all()

        if position_filter:
            mapping = {'BUY': 'LONG', 'SELL': 'SHORT'}
            if position_filter.upper() not in mapping:
                return Response({'error': 'Choose BUY or SELL'}, status=400)
            trades = trades.filter(position=mapping[position_filter.upper()])

        serializer = TradeSerializer(trades, many=True)
        return Response({
            'trades': serializer.data,
            'buyers_count': market.long_trades_count,
            'sellers_count': market.short_trades_count,
            'total_count': market.total_trades_count
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def close_trading(request, market_id):
    """
    Manually close trading on a market (admin only)
    """
    try:
        market = get_object_or_404(Market.objects.select_for_update(), id=market_id)
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)

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

    except Http404:
        raise
    except Exception as e:
        return create_error_response(f"Error closing market: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def set_settlement_price(request, market_id):
    """
    Set settlement price for a closed market (admin only)
    """
    try:
        market = get_object_or_404(Market.objects.select_for_update(), id=market_id)
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)

        # New rule: Settlement price can be changed until confirmed
        if market.settlement_confirmed:
            return create_error_response("Cannot change settlement price after settlement has been confirmed", status_code=status.HTTP_400_BAD_REQUEST)

        if market.status not in ['CLOSED', 'SETTLED']:
            return create_error_response("Market must be CLOSED before setting settlement price", status_code=status.HTTP_400_BAD_REQUEST)

        price = request.data.get('price')
        if price is None:
            return create_error_response("Settlement price is required", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            price = Decimal(str(price))
        except (ValueError, TypeError, InvalidOperation):
            return create_error_response("Invalid price format", status_code=status.HTTP_400_BAD_REQUEST)

        # Validate price range
        if not price.is_finite() or price.as_tuple().exponent < -2 or not (Decimal('0.01') <= price <= Decimal('999999.99')):
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
    except Http404:
        raise
    except Exception as e:
        return create_error_response(f"Error setting settlement price: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def settlement_preview(request, market_id):
    """
    Get settlement preview showing all trade impacts (admin only)
    """
    try:
        market = get_object_or_404(Market.objects.select_for_update(), id=market_id)
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)

        if market.settlement_price is None:
            return create_error_response("Settlement price must be set before preview", status_code=status.HTTP_400_BAD_REQUEST)

        settlement_data = calculate_settlement_preview(market)

        return create_success_response(
            "Settlement preview calculated successfully",
            settlement_data
        )

    except ValidationError as e:
        return create_error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Http404:
        raise
    except Exception as e:
        return create_error_response(f"Error calculating settlement preview: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def execute_settlement(request, market_id):
    """
    Execute final settlement and update all user balances (admin only)
    """
    try:
        market = get_object_or_404(Market.objects.select_for_update(), id=market_id)
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)

        confirmed = request.data.get('confirmed', False)
        if confirmed is not True:
            return create_error_response("Admin confirmation required - set 'confirmed': true", status_code=status.HTTP_400_BAD_REQUEST)

        result = settle_market(market, confirmed_by_admin=True, preview_version=request.data.get('preview_version'))

        if result['success']:
            return create_success_response(
                result['message'],
                result
            )
        else:
            return create_error_response(result['message'], status_code=status.HTTP_400_BAD_REQUEST)

    except ValidationError as e:
        return create_error_response(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Http404:
        raise
    except Exception as e:
        return create_error_response(f"Error executing settlement: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def reopen_trading(request, market_id):
    """
    Reopen trading for a closed market with new close time (admin only)
    """
    try:
        market = get_object_or_404(Market.objects.select_for_update(), id=market_id)
        if market.created_by_id != request.user.id:
            return Response({'error': 'Only the market administrator can do this'}, status=403)

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
    except Http404:
        raise
    except Exception as e:
        return create_error_response(f"Error reopening market: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def settled_market_trades(request, market_id=None):
    """
    Get public trade history for settled markets - all users can see positions and P&L
    Business Rule: Once settled, all users should be able to see who bet, their position, and P&L
    """
    try:
        if market_id:
            # Get trades for specific settled market
            market = get_object_or_404(Market, id=market_id)
            if market.status != 'SETTLED':
                return create_error_response("Market must be settled to view public trade details", status_code=status.HTTP_400_BAD_REQUEST)

            trades = Trade.objects.filter(
                market=market,
                is_settled=True
            ).select_related('market', 'user').order_by('-trade_time')

        else:
            # Get all trades from all settled markets
            trades = Trade.objects.filter(
                market__status='SETTLED',
                is_settled=True
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
                'trader': trade.user.username,  # Public visibility for settled markets
                'position': 'BUY' if trade.position == 'LONG' else 'SELL',
                'trade_price': float(trade.price),
                'trade_time': trade.trade_time.isoformat(),
                'settlement_amount': float(trade.settlement_amount) if trade.settlement_amount else 0,
                'profit_loss': float(trade.profit_loss) if trade.profit_loss else 0,
                'won': (
                    (trade.position == 'LONG' and trade.profit_loss > 0) or
                    (trade.position == 'SHORT' and trade.profit_loss > 0)
                ) if trade.profit_loss is not None else None,
            }
            trade_data.append(trade_info)

        return create_success_response(
            "Settled market trades retrieved successfully",
            {
                'trades': trade_data,
                'total_trades': len(trade_data),
                'market_id': market_id if market_id else 'all',
                'note': 'Public trade details for settled markets only.'
            }
        )

    except Http404:
        raise
    except Exception as e:
        return create_error_response(f"Error retrieving settled market trades: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
