from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Market, SpreadBid, Trade
import logging

logger = logging.getLogger(__name__)

class MarketSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    is_spread_bidding_active = serializers.ReadOnlyField()
    is_trading_active = serializers.ReadOnlyField()
    can_be_settled = serializers.ReadOnlyField()
    current_spread_display = serializers.ReadOnlyField()
    best_spread_bid = serializers.SerializerMethodField()
    current_best_spread_width = serializers.ReadOnlyField()
    
    # Add timezone debugging fields
    server_time = serializers.SerializerMethodField()
    timezone_info = serializers.SerializerMethodField()
    
    # Add trade statistics
    long_trades_count = serializers.ReadOnlyField()
    short_trades_count = serializers.ReadOnlyField()
    total_trades_count = serializers.ReadOnlyField()
    user_trade = serializers.SerializerMethodField()
    can_user_trade = serializers.SerializerMethodField()
    
    class Meta:
        model = Market
        fields = [
            'id',
            'premise',
            'unit_price',
            'initial_spread',
            'final_spread_low',
            'final_spread_high',
            'current_spread_display',
            'created_by',
            'created_by_username',
            'status',
            'spread_bidding_open',
            'spread_bidding_close',
            'trading_open',
            'trading_close',
            'outcome',
            'is_spread_bidding_active',
            'is_trading_active',
            'can_be_settled',
            'best_spread_bid',
            'current_best_spread_width',
            'created_at',
            'updated_at',
            'server_time',
            'timezone_info',
            'long_trades_count',
            'short_trades_count',
            'total_trades_count',
            'user_trade',
            'can_user_trade'
        ]
        read_only_fields = ['created_at', 'updated_at', 'final_spread_low', 'final_spread_high']
    
    def get_best_spread_bid(self, obj):
        """Get the best spread bid for this market"""
        best_bid = obj.best_spread_bid
        if best_bid:
            return {
                'id': best_bid.id,
                'user': best_bid.user.username,
                'spread_width': best_bid.spread_width,
                'bid_time': best_bid.bid_time
            }
        return None
    
    def get_server_time(self, obj):
        """Return current server time for timezone debugging"""
        return timezone.now()
    
    def get_timezone_info(self, obj):
        """Return timezone information for debugging"""
        return {
            'server_timezone': str(timezone.get_current_timezone()),
            'utc_offset': timezone.now().strftime('%z'),
            'is_dst': timezone.now().dst() is not None
        }
    
    def get_user_trade(self, obj):
        """Get the current user's trade on this market (if any)"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            trade = obj.get_user_trade(request.user)
            if trade:
                return {
                    'id': trade.id,
                    'position': trade.position,
                    'price': trade.price,
                    'quantity': trade.quantity,
                    'total_value': trade.total_value,
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
    """Serializer for creating new markets"""
    
    class Meta:
        model = Market
        fields = [
            'premise',
            'unit_price',
            'initial_spread',
            'spread_bidding_open',
            'spread_bidding_close',
            'trading_open',
            'trading_close'
        ]
    
    def validate(self, data):
        """Validate market timing"""
        if data['spread_bidding_open'] >= data['spread_bidding_close']:
            raise serializers.ValidationError(
                "Spread bidding close must be after spread bidding open"
            )
        
        if data['trading_open'] >= data['trading_close']:
            raise serializers.ValidationError(
                "Trading close must be after trading open"
            )
        
        if data['spread_bidding_close'] > data['trading_open']:
            raise serializers.ValidationError(
                "Trading open must be after spread bidding close"
            )
        
        if data['initial_spread'] <= 0:
            raise serializers.ValidationError(
                "Initial spread must be greater than 0"
            )
        
        return data

class MarketUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating market status, outcome, and final spread"""
    
    class Meta:
        model = Market
        fields = ['status', 'outcome', 'final_spread_low', 'final_spread_high']
    
    def validate(self, data):
        """Validate status transitions and spread updates"""
        instance = self.instance
        new_status = data.get('status', instance.status)
        
        # Define valid status transitions
        valid_transitions = {
            'CREATED': ['OPEN'],
            'OPEN': ['CLOSED'],
            'CLOSED': ['SETTLED'],
            'SETTLED': []  # No transitions from settled
        }
        
        if new_status != instance.status:
            if new_status not in valid_transitions.get(instance.status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from {instance.status} to {new_status}"
                )
        
        # Outcome is required when settling
        if new_status == 'SETTLED' and not data.get('outcome'):
            raise serializers.ValidationError(
                "Outcome is required when settling a market"
            )
        
        # Validate final spread if provided
        final_low = data.get('final_spread_low')
        final_high = data.get('final_spread_high')
        
        if final_low is not None and final_high is not None:
            if final_low >= final_high:
                raise serializers.ValidationError(
                    "Final spread high must be greater than final spread low"
                )
        elif final_low is not None or final_high is not None:
            raise serializers.ValidationError(
                "Both final_spread_low and final_spread_high must be provided together"
            )
        
        return data

class MarketEditSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for admin editing of markets"""
    
    class Meta:
        model = Market
        fields = [
            'premise',
            'unit_price',
            'initial_spread',
            'spread_bidding_open',
            'spread_bidding_close',
            'trading_open',
            'trading_close',
            'status',
            'outcome'
        ]
    
    def validate(self, data):
        """Validate market data with business rules"""
        instance = self.instance
        
        # Get current or new values
        premise = data.get('premise', instance.premise)
        unit_price = data.get('unit_price', instance.unit_price)
        initial_spread = data.get('initial_spread', instance.initial_spread)
        spread_bidding_open = data.get('spread_bidding_open', instance.spread_bidding_open)
        spread_bidding_close = data.get('spread_bidding_close', instance.spread_bidding_close)
        trading_open = data.get('trading_open', instance.trading_open)
        trading_close = data.get('trading_close', instance.trading_close)
        new_status = data.get('status', instance.status)
        
        # Basic validations
        if unit_price <= 0:
            raise serializers.ValidationError("Unit price must be greater than 0")
        
        if initial_spread <= 0:
            raise serializers.ValidationError("Initial spread must be greater than 0")
        
        # Timing validations
        if spread_bidding_open >= spread_bidding_close:
            raise serializers.ValidationError(
                "Spread bidding close must be after spread bidding open"
            )
        
        if trading_open >= trading_close:
            raise serializers.ValidationError(
                "Trading close must be after trading open"
            )
        
        if spread_bidding_close > trading_open:
            raise serializers.ValidationError(
                "Trading open must be after spread bidding close"
            )
        
        # Business rule validations based on current state
        now = timezone.now()
        
        # If market has started (has bids or is past bidding phase), restrict certain changes
        if instance.spread_bids.exists() or now > instance.spread_bidding_open:
            # Don't allow changing core market parameters if bidding has started
            if (data.get('premise') and data['premise'] != instance.premise):
                raise serializers.ValidationError(
                    "Cannot change market premise after bidding has started"
                )
            
            if (data.get('initial_spread') and data['initial_spread'] != instance.initial_spread):
                raise serializers.ValidationError(
                    "Cannot change initial spread after bidding has started"
                )
        
        # If market is past spread bidding phase, don't allow changing bidding times
        if now > instance.spread_bidding_close:
            if (data.get('spread_bidding_open') and 
                data['spread_bidding_open'] != instance.spread_bidding_open):
                raise serializers.ValidationError(
                    "Cannot change spread bidding times after bidding has closed"
                )
            
            if (data.get('spread_bidding_close') and 
                data['spread_bidding_close'] != instance.spread_bidding_close):
                raise serializers.ValidationError(
                    "Cannot change spread bidding times after bidding has closed"
                )
        
        # Status transition validation
        valid_transitions = {
            'CREATED': ['OPEN'],
            'OPEN': ['CLOSED'],
            'CLOSED': ['SETTLED'],
            'SETTLED': []
        }
        
        if new_status != instance.status:
            if new_status not in valid_transitions.get(instance.status, []):
                raise serializers.ValidationError(
                    f"Cannot transition from {instance.status} to {new_status}"
                )
        
        # Outcome validation
        if new_status == 'SETTLED' and not data.get('outcome'):
            raise serializers.ValidationError(
                "Outcome is required when settling a market"
            )
        
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
        
        # Check if user is verified
        if not hasattr(user, 'profile') or not user.profile.is_verified:
            raise serializers.ValidationError(
                "Only verified users can place spread bids"
            )
        
        # Check if market is in CREATED state
        if market.status != 'CREATED':
            raise serializers.ValidationError(
                "Can only bid on markets in CREATED state"
            )
        
        # Check if spread bidding window is active
        now = timezone.now()
        if not (market.spread_bidding_open <= now <= market.spread_bidding_close):
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
        
        # Check if this bid is tighter than the current best spread
        current_best_width = market.current_best_spread_width
        if new_spread_width >= current_best_width:
            raise serializers.ValidationError(
                f"New bid must be tighter than current best spread width of {current_best_width}"
            )
        
        # Check if this bid is tighter than user's previous bids
        user_best_bid = market.get_user_best_bid(user)
        if user_best_bid and new_spread_width >= user_best_bid.spread_width:
            raise serializers.ValidationError(
                f"New bid must be tighter than your previous best bid of {user_best_bid.spread_width}"
            )
        
        return data
    
    def create(self, validated_data):
        """Create spread bid with current user"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TradeSerializer(serializers.ModelSerializer):
    """Serializer for displaying trades"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    market_premise = serializers.CharField(source='market.premise', read_only=True)
    is_long = serializers.ReadOnlyField()
    is_short = serializers.ReadOnlyField()
    total_value = serializers.ReadOnlyField()
    
    class Meta:
        model = Trade
        fields = [
            'id',
            'market',
            'market_premise',
            'user',
            'user_username',
            'position',
            'price',
            'quantity',
            'total_value',
            'is_long',
            'is_short',
            'trade_time',
            'updated_at'
        ]
        read_only_fields = ['trade_time', 'updated_at', 'user']


class TradeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new trades"""
    
    class Meta:
        model = Trade
        fields = ['market', 'position', 'price', 'quantity']
    
    def validate(self, data):
        """Validate trade creation rules"""
        market = data['market']
        user = self.context['request'].user
        position = data['position']
        price = data['price']
        quantity = data.get('quantity', 1)
        
        # Check if user can trade on this market
        can_trade, reason = market.can_user_trade(user)
        if not can_trade:
            raise serializers.ValidationError(reason)
        
        # Check if market is open for trading
        if not market.is_trading_active:
            raise serializers.ValidationError("Market is not open for trading")
        
        # Validate price is within market spread
        if market.final_spread_low is not None and market.final_spread_high is not None:
            if position == 'LONG' and price < market.final_spread_high:
                raise serializers.ValidationError(
                    f"Long position price must be at least {market.final_spread_high}"
                )
            elif position == 'SHORT' and price > market.final_spread_low:
                raise serializers.ValidationError(
                    f"Short position price must be at most {market.final_spread_low}"
                )
        
        # Validate quantity
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        
        # Validate price
        if price <= 0:
            raise serializers.ValidationError("Price must be positive")
        
        return data
    
    def create(self, validated_data):
        """Create a new trade"""
        validated_data['user'] = self.context['request'].user
        return Trade.objects.create(**validated_data)


class TradeUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating existing trades"""
    
    class Meta:
        model = Trade
        fields = ['position', 'price', 'quantity']
    
    def validate(self, data):
        """Validate trade update rules"""
        instance = self.instance
        market = instance.market
        
        # Check if market is still open for trading
        if not market.is_trading_active:
            raise serializers.ValidationError("Cannot update trade - market is closed")
        
        # Get new values or keep existing ones
        position = data.get('position', instance.position)
        price = data.get('price', instance.price)
        quantity = data.get('quantity', instance.quantity)
        
        # Validate price is within market spread
        if market.final_spread_low is not None and market.final_spread_high is not None:
            if position == 'LONG' and price < market.final_spread_high:
                raise serializers.ValidationError(
                    f"Long position price must be at least {market.final_spread_high}"
                )
            elif position == 'SHORT' and price > market.final_spread_low:
                raise serializers.ValidationError(
                    f"Short position price must be at most {market.final_spread_low}"
                )
        
        # Validate quantity and price
        if quantity <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        
        if price <= 0:
            raise serializers.ValidationError("Price must be positive")
        
        return data 