from rest_framework import serializers
from django.utils import timezone
from .models import Market, SpreadBid, Trade

class MarketSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    market_maker_username = serializers.CharField(source='market_maker.username', read_only=True)
    is_spread_bidding_active = serializers.ReadOnlyField()
    is_trading_active = serializers.ReadOnlyField()
    can_be_settled = serializers.ReadOnlyField()
    current_spread_display = serializers.ReadOnlyField()
    best_spread_bid = serializers.SerializerMethodField()
    position_display = serializers.SerializerMethodField()
    top_quotes = serializers.SerializerMethodField()
    personal_rank = serializers.SerializerMethodField()
    unit_value = serializers.DecimalField(source='unit_price', max_digits=10, decimal_places=2, read_only=True)
    current_best_spread_width = serializers.ReadOnlyField()
    
    
    # Add trade statistics
    total_trades_count = serializers.ReadOnlyField()
    user_trade = serializers.SerializerMethodField()
    can_user_trade = serializers.SerializerMethodField()
    
    class Meta:
        model = Market
        fields = [
            'id',
            'premise',
            'final_spread_low',
            'final_spread_high',
            'current_spread_display',
            'created_by',
            'created_by_username',
            'market_maker',
            'market_maker_username',
            'market_maker_spread_low',
            'market_maker_spread_high',
            'status',
            'spread_bidding_open',
            'spread_bidding_close_trading_open',
            'trading_close',
            'settlement_price',
            'settled_at',
            'settlement_confirmed',
            'settlement_preview_calculated',
            'is_spread_bidding_active',
            'is_trading_active',
            'can_be_settled',
            'best_spread_bid', 'position_display', 'top_quotes', 'personal_rank', 'unit_value',
            'current_best_spread_width',
            'created_at',
            'updated_at',
            'total_trades_count',
            'user_trade',
            'can_user_trade'
        ]
        read_only_fields = ['created_at', 'updated_at', 'final_spread_low', 'final_spread_high']
    
    def get_position_display(self, obj):
        result = {}
        for label, position in (('buyers', 'LONG'), ('sellers', 'SHORT')):
            names = list(obj.trades.filter(position=position).values_list('user__username', flat=True))
            request = self.context.get('request')
            authenticated = request and request.user.is_authenticated
            result[label] = {'count': len(names), 'names': names if authenticated and len(names) <= 7 else []}
        return result

    def _ranked_quotes(self, obj):
        latest = {}
        for bid in obj.spread_bids.select_related('user').order_by('bid_time', 'id'):
            latest[bid.user_id] = bid
        return sorted(latest.values(), key=lambda b: (b.spread_width, b.bid_time, b.id))

    def get_top_quotes(self, obj):
        request = self.context.get('request')
        return SpreadBidSerializer(self._ranked_quotes(obj)[:3], many=True).data if request and request.user.is_authenticated else []

    def get_personal_rank(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return next((i for i, bid in enumerate(self._ranked_quotes(obj), 1) if bid.user_id == request.user.id), None)
        return None

    def get_best_spread_bid(self, obj):
        """Get the best spread bid for this market"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        best_bid = obj.best_spread_bid
        if best_bid:
            return {
                'id': best_bid.id,
                'user': best_bid.user.username,
                'spread_width': best_bid.spread_width,
                'bid_time': best_bid.bid_time
            }
        return None
    
    def get_user_trade(self, obj):
        """Get the current user's trade on this market (if any)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            trade = obj.get_user_trade(request.user)
            if trade:
                return {
                    'id': trade.id,
                    'position': 'BUY' if trade.position == 'LONG' else 'SELL',
                    'price': trade.price,
                    'trade_time': trade.trade_time,
                    'updated_at': trade.updated_at
                }
        return None
    
    def get_can_user_trade(self, obj):
        """Check if the current user can trade on this market"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            can_trade, reason = obj.can_user_trade(request.user)
            return {
                'can_trade': can_trade,
                'reason': reason
            }
        return {
            'can_trade': False,
            'reason': 'User not authenticated'
        }

class MarketCreateSerializer(serializers.ModelSerializer):
    unit_value = serializers.DecimalField(source='unit_price', max_digits=10, decimal_places=2, min_value=0.01)
    """Serializer for creating new markets"""
    
    class Meta:
        model = Market
        fields = [
            'premise',
            'unit_value',
            'spread_bidding_open',
            'spread_bidding_close_trading_open',
            'trading_close'
        ]
    
    def validate(self, data):
        """Validate market timing and reject obsolete input fields."""
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError(f'Unknown fields: {", ".join(sorted(unknown))}')
        if data['spread_bidding_open'] >= data['spread_bidding_close_trading_open']:
            raise serializers.ValidationError(
                "Spread bidding close & trading open must be after spread bidding open"
            )
        
        if data['spread_bidding_close_trading_open'] >= data['trading_close']:
            raise serializers.ValidationError(
                "Trading close must be after spread bidding close & trading open"
            )
        
        if data['unit_price'] <= 0:
            raise serializers.ValidationError('Unit value must be positive')
        
        return data

class MarketEditSerializer(serializers.ModelSerializer):
    unit_value = serializers.DecimalField(source='unit_price', max_digits=10, decimal_places=2, min_value=0.01, required=False)

    class Meta:
        model = Market
        fields = ['premise', 'unit_value', 'spread_bidding_open', 'spread_bidding_close_trading_open', 'trading_close']

    def validate(self, data):
        instance = self.instance
        start = data.get('spread_bidding_open', instance.spread_bidding_open)
        bidding_close = data.get('spread_bidding_close_trading_open', instance.spread_bidding_close_trading_open)
        close = data.get('trading_close', instance.trading_close)
        if not start < bidding_close < close:
            raise serializers.ValidationError('Deadlines must be in order')
        if data.get('premise', instance.premise) != instance.premise and (instance.spread_bids.exists() or timezone.now() > instance.spread_bidding_open):
            raise serializers.ValidationError('Cannot change question after bidding starts')
        if instance.status != 'CREATED' and ('spread_bidding_open' in data or 'spread_bidding_close_trading_open' in data):
            raise serializers.ValidationError('Bidding deadlines cannot be changed after activation')
        return data

class SpreadBidSerializer(serializers.ModelSerializer):
    """Serializer for displaying spread bids"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    spread_width = serializers.ReadOnlyField()
    spread_display = serializers.ReadOnlyField()
    
    class Meta:
        model = SpreadBid
        fields = [
            'id',
            'market',
            'user',
            'user_username',
            'spread_low',
            'spread_high',
            'spread_width',
            'spread_display',
            'bid_time'
        ]
        read_only_fields = ['bid_time', 'user']


class SpreadBidCreateSerializer(serializers.ModelSerializer):
    spread_low = serializers.IntegerField(min_value=1, max_value=99999999)
    spread_high = serializers.IntegerField(min_value=1, max_value=99999999)
    """Serializer for creating new spread bids"""
    
    class Meta:
        model = SpreadBid
        fields = ['market', 'spread_low', 'spread_high']
    
    def validate(self, data):
        """Validate spread bid rules"""
        market = data['market']
        user = self.context['request'].user
        spread_low = data['spread_low']
        spread_high = data['spread_high']
        
        if market.created_by_id == user.id:
            raise serializers.ValidationError("Market administrator cannot bid")

        # Check if market is in CREATED state
        if market.status != 'CREATED':
            raise serializers.ValidationError(
                "Can only bid on markets in CREATED state"
            )
        
        # Check if spread bidding window is active
        now = timezone.now()
        if not (market.spread_bidding_open <= now < market.spread_bidding_close_trading_open):
            raise serializers.ValidationError(
                "Spread bidding is not currently active for this market"
            )
        
        # Validate spread values
        if spread_low >= spread_high:
            raise serializers.ValidationError(
                "Spread low must be less than spread high"
            )
        
        new_spread_width = spread_high - spread_low
        
        if new_spread_width <= 0:
            raise serializers.ValidationError(
                "Spread width must be positive"
            )
        
        return data
    
    def create(self, validated_data):
        """Create spread bid with current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TradeSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    position = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        fields = ['id', 'user_username', 'position', 'price', 'trade_time', 'updated_at']

    def get_position(self, obj):
        return 'BUY' if obj.position == 'LONG' else 'SELL'
