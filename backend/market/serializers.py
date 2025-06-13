from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Market

class MarketSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    is_spread_bidding_active = serializers.ReadOnlyField()
    is_trading_active = serializers.ReadOnlyField()
    can_be_settled = serializers.ReadOnlyField()
    current_spread_display = serializers.ReadOnlyField()
    
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
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'final_spread_low', 'final_spread_high']

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