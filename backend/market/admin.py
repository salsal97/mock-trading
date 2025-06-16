from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
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
        'should_auto_activate',
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
    readonly_fields = [
        'created_at', 
        'updated_at', 
        'is_spread_bidding_active', 
        'is_trading_active', 
        'can_be_settled', 
        'current_spread_display',
        'should_auto_activate',
        'best_spread_bid_info'
    ]
    actions = ['auto_activate_selected_markets']
    
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
            'fields': (
                'is_spread_bidding_active', 
                'is_trading_active', 
                'can_be_settled',
                'should_auto_activate',
                'best_spread_bid_info'
            ),
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
    
    def should_auto_activate(self, obj):
        """Display if market should be auto-activated"""
        return obj.should_auto_activate
    should_auto_activate.boolean = True
    should_auto_activate.short_description = 'Should Auto-Activate'
    
    def best_spread_bid_info(self, obj):
        """Display information about the best spread bid"""
        best_bid = obj.best_spread_bid
        if best_bid:
            return format_html(
                '<strong>User:</strong> {} <br>'
                '<strong>Spread:</strong> {}-{} <br>'
                '<strong>Width:</strong> {} <br>'
                '<strong>Time:</strong> {}',
                best_bid.user.username,
                best_bid.spread_low,
                best_bid.spread_high,
                best_bid.spread_width,
                best_bid.bid_time.strftime('%Y-%m-%d %H:%M:%S')
            )
        return "No bids"
    best_spread_bid_info.short_description = 'Best Spread Bid'
    
    def auto_activate_selected_markets(self, request, queryset):
        """Admin action to auto-activate selected markets"""
        activated_count = 0
        failed_count = 0
        messages = []
        
        for market in queryset:
            if market.should_auto_activate:
                result = market.auto_activate_market()
                if result['success']:
                    activated_count += 1
                    messages.append(f"✓ Market {market.id}: {result['reason']}")
                else:
                    failed_count += 1
                    messages.append(f"✗ Market {market.id}: {result['reason']}")
            else:
                messages.append(f"- Market {market.id}: Not eligible for auto-activation")
        
        # Create summary message
        summary = f"Processed {queryset.count()} markets: {activated_count} activated, {failed_count} failed"
        if messages:
            full_message = summary + "\n\nDetails:\n" + "\n".join(messages)
        else:
            full_message = summary
        
        if activated_count > 0:
            self.message_user(request, full_message)
        else:
            self.message_user(request, full_message, level='warning')
    
    auto_activate_selected_markets.short_description = "Auto-activate selected markets"


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
