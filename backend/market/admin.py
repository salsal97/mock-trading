from django.contrib import admin
from .models import Market, SpreadBid

@admin.register(Market)
class MarketAdmin(admin.ModelAdmin):
    list_display = [
        'premise_short', 
        'status', 
        'unit_price', 
        'current_spread_display',
        'created_by', 
        'trading_open', 
        'trading_close',
        'is_trading_active',
        'created_at'
    ]
    list_filter = [
        'status', 
        'created_by', 
        'created_at',
        'trading_open',
        'trading_close'
    ]
    search_fields = ['premise', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at', 'is_spread_bidding_active', 'is_trading_active', 'can_be_settled', 'current_spread_display']
    
    fieldsets = (
        ('Market Information', {
            'fields': ('premise', 'unit_price', 'initial_spread', 'created_by', 'status')
        }),
        ('Final Spread (Set through bidding)', {
            'fields': ('final_spread_low', 'final_spread_high', 'current_spread_display'),
            'classes': ('collapse',)
        }),
        ('Timing', {
            'fields': ('spread_bidding_open', 'spread_bidding_close', 'trading_open', 'trading_close')
        }),
        ('Settlement', {
            'fields': ('outcome',)
        }),
        ('Status Information', {
            'fields': ('is_spread_bidding_active', 'is_trading_active', 'can_be_settled'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def premise_short(self, obj):
        """Display shortened premise"""
        return obj.premise[:50] + "..." if len(obj.premise) > 50 else obj.premise
    premise_short.short_description = 'Premise'
    
    def is_trading_active(self, obj):
        """Display if trading is active"""
        return obj.is_trading_active
    is_trading_active.boolean = True
    is_trading_active.short_description = 'Trading Active'


@admin.register(SpreadBid)
class SpreadBidAdmin(admin.ModelAdmin):
    list_display = [
        'market_short',
        'user',
        'spread_width',
        'bid_time',
        'is_best_bid'
    ]
    list_filter = [
        'market',
        'user',
        'bid_time'
    ]
    search_fields = ['market__premise', 'user__username']
    readonly_fields = ['bid_time', 'spread_width', 'spread_display']
    
    fieldsets = (
        ('Bid Information', {
            'fields': ('market', 'user', 'spread_width')
        }),
        ('Detailed Spread Values', {
            'fields': ('spread_low', 'spread_high', 'spread_display'),
            'classes': ('collapse',),
            'description': 'Individual spread values (collapsed for privacy)'
        }),
        ('Timestamp', {
            'fields': ('bid_time',),
            'classes': ('collapse',)
        }),
    )
    
    def market_short(self, obj):
        """Display shortened market premise"""
        return obj.market.premise[:30] + "..." if len(obj.market.premise) > 30 else obj.market.premise
    market_short.short_description = 'Market'
    
    def is_best_bid(self, obj):
        """Check if this is the best bid for the market"""
        return obj.market.best_spread_bid == obj
    is_best_bid.boolean = True
    is_best_bid.short_description = 'Best Bid'
