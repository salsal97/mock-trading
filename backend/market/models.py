from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Market(models.Model):
    STATUS_CHOICES = [
        ('CREATED', 'Created'),
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
        ('SETTLED', 'Settled'),
    ]
    
    premise = models.CharField(max_length=500, help_text="The market premise or question")
    unit_price = models.FloatField(help_text="Base unit price for trading")
    initial_spread = models.IntegerField(help_text="Initial spread value set when creating the market")
    
    # Final spread range (set through bidding process)
    final_spread_low = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Lower bound of the final spread (set through bidding)"
    )
    final_spread_high = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Upper bound of the final spread (set through bidding)"
    )
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='created_markets',
        help_text="User who created this market"
    )
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='CREATED',
        help_text="Current status of the market"
    )
    spread_bidding_open = models.DateTimeField(
        help_text="When spread bidding opens"
    )
    spread_bidding_close = models.DateTimeField(
        help_text="When spread bidding closes"
    )
    trading_open = models.DateTimeField(
        help_text="When trading opens"
    )
    trading_close = models.DateTimeField(
        help_text="When trading closes"
    )
    outcome = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Final outcome of the market (set when settled)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Market'
        verbose_name_plural = 'Markets'
    
    def __str__(self):
        return f"{self.premise[:50]}... - {self.status}"
    
    @property
    def is_spread_bidding_active(self):
        """Check if spread bidding is currently active"""
        now = timezone.now()
        return self.spread_bidding_open <= now <= self.spread_bidding_close
    
    @property
    def is_trading_active(self):
        """Check if trading is currently active"""
        now = timezone.now()
        return self.trading_open <= now <= self.trading_close and self.status == 'OPEN'
    
    @property
    def can_be_settled(self):
        """Check if market can be settled"""
        now = timezone.now()
        return now > self.trading_close and self.status == 'CLOSED'
    
    @property
    def should_auto_activate(self):
        """Check if market should be automatically activated"""
        now = timezone.now()
        return (
            self.status == 'CREATED' and 
            now > self.spread_bidding_close and 
            self.final_spread_low is None and 
            self.final_spread_high is None
        )
    
    @property
    def current_spread_display(self):
        """Display current spread - shows best bid width during bidding, final range after"""
        # If market has final spread set (after bidding), show the range
        if self.final_spread_low is not None and self.final_spread_high is not None:
            return f"{self.final_spread_low} - {self.final_spread_high}"
        
        # During spread bidding phase, show the current best width
        if self.status == 'CREATED' and self.best_spread_bid:
            return f"Best: {self.current_best_spread_width}"
        
        # Default to initial spread
        return f"Initial: {self.initial_spread}"
    
    @property
    def best_spread_bid(self):
        """Get the current best (tightest) spread bid"""
        bids = list(self.spread_bids.all())
        if not bids:
            return None
        # Sort by spread width (tightest first), then by bid time (earliest first)
        return min(bids, key=lambda bid: (bid.spread_width, bid.bid_time))
    
    @property
    def current_best_spread_width(self):
        """Get the width of the current best spread bid, or initial spread if no bids"""
        best_bid = self.best_spread_bid
        if best_bid:
            return best_bid.spread_width
        return self.initial_spread
    
    def get_user_best_bid(self, user):
        """Get a user's best (tightest) bid on this market"""
        user_bids = list(self.spread_bids.filter(user=user))
        if not user_bids:
            return None
        # Sort by spread width (tightest first), then by bid time (earliest first)
        return min(user_bids, key=lambda bid: (bid.spread_width, bid.bid_time))
    
    @property
    def long_trades_count(self):
        """Get count of long positions on this market"""
        return self.trades.filter(position='LONG').count()
    
    @property
    def short_trades_count(self):
        """Get count of short positions on this market"""
        return self.trades.filter(position='SHORT').count()
    
    @property
    def total_trades_count(self):
        """Get total number of trades on this market"""
        return self.trades.count()
    
    def get_user_trade(self, user):
        """Get a user's trade on this market (if any)"""
        try:
            return self.trades.get(user=user)
        except:
            return None
    
    def can_user_trade(self, user):
        """Check if a user can place a trade on this market"""
        # Market must be open for trading
        if not self.is_trading_active:
            return False, "Market is not open for trading"
        
        # User must be verified (if profile exists)
        if hasattr(user, 'profile') and not user.profile.is_verified:
            return False, "Only verified users can trade"
        
        # User cannot be the market maker
        if self.created_by == user:
            return False, "Market makers cannot trade on their own markets"
        
        return True, "User can trade"
    
    def auto_activate_market(self):
        """
        Automatically activate the market by selecting the winning spread bid.
        
        This method:
        1. Picks the bid with the lowest spread (tie-breaker: earliest timestamp)
        2. Sets final_spread_low, final_spread_high from the winning bid
        3. Updates created_by to the winning bidder
        4. Changes market.status to OPEN
        
        Returns:
            dict: Result of the activation with success status and details
        """
        try:
            # Check if market is eligible for auto-activation
            if not self.should_auto_activate:
                return {
                    'success': False,
                    'reason': 'Market is not eligible for auto-activation',
                    'details': {
                        'status': self.status,
                        'bidding_closed': timezone.now() > self.spread_bidding_close,
                        'already_activated': self.final_spread_low is not None
                    }
                }
            
            # Get the winning bid
            winning_bid = self.best_spread_bid
            
            if not winning_bid:
                # No bids received - use initial spread and keep original creator
                logger.info(f"Market {self.id}: No bids received, using initial spread")
                self.final_spread_low = 50 - (self.initial_spread // 2)
                self.final_spread_high = 50 + (self.initial_spread // 2)
                # Keep original created_by
                self.status = 'OPEN'
                self.save()
                
                return {
                    'success': True,
                    'reason': 'No bids received, activated with initial spread',
                    'details': {
                        'winning_bid': None,
                        'final_spread_low': self.final_spread_low,
                        'final_spread_high': self.final_spread_high,
                        'market_maker': self.created_by.username
                    }
                }
            
            # Apply winning bid
            logger.info(f"Market {self.id}: Activating with winning bid from {winning_bid.user.username}")
            
            self.final_spread_low = winning_bid.spread_low
            self.final_spread_high = winning_bid.spread_high
            self.created_by = winning_bid.user  # Winner becomes the market maker
            self.status = 'OPEN'
            self.save()
            
            return {
                'success': True,
                'reason': 'Market activated with winning bid',
                'details': {
                    'winning_bid': {
                        'id': winning_bid.id,
                        'user': winning_bid.user.username,
                        'spread_low': winning_bid.spread_low,
                        'spread_high': winning_bid.spread_high,
                        'spread_width': winning_bid.spread_width,
                        'bid_time': winning_bid.bid_time
                    },
                    'final_spread_low': self.final_spread_low,
                    'final_spread_high': self.final_spread_high,
                    'market_maker': self.created_by.username
                }
            }
            
        except Exception as e:
            logger.error(f"Error auto-activating market {self.id}: {str(e)}")
            return {
                'success': False,
                'reason': f'Error during activation: {str(e)}',
                'details': {'error': str(e)}
            }


class SpreadBid(models.Model):
    """Model for spread bidding - users compete to become market makers"""
    
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='spread_bids',
        help_text="The market this bid is for"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='spread_bids',
        help_text="User placing the bid"
    )
    spread_low = models.IntegerField(
        help_text="Lower bound of the spread bid"
    )
    spread_high = models.IntegerField(
        help_text="Upper bound of the spread bid"
    )
    bid_time = models.DateTimeField(
        auto_now_add=True,
        help_text="When this bid was placed"
    )
    
    class Meta:
        ordering = ['bid_time']  # Order by time of bid
        verbose_name = 'Spread Bid'
        verbose_name_plural = 'Spread Bids'
        indexes = [
            models.Index(fields=['market', 'bid_time']),
            models.Index(fields=['user', 'market', 'bid_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.spread_low}-{self.spread_high} on {self.market.premise[:30]}..."
    
    @property
    def spread_width(self):
        """Calculate the width of this spread (smaller is better)"""
        return self.spread_high - self.spread_low
    
    @property
    def spread_display(self):
        """Display format for the spread"""
        return f"{self.spread_low} - {self.spread_high}"
    
    def clean(self):
        """Validate the spread bid"""
        from django.core.exceptions import ValidationError
        
        if self.spread_low >= self.spread_high:
            raise ValidationError("Spread low must be less than spread high")
        
        if self.spread_width <= 0:
            raise ValidationError("Spread width must be positive")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)


class Trade(models.Model):
    """Model for tracking user trading positions on markets"""
    
    POSITION_CHOICES = [
        ('LONG', 'Long'),
        ('SHORT', 'Short'),
    ]
    
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='trades',
        help_text="The market this trade is for"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trades',
        help_text="User placing the trade"
    )
    position = models.CharField(
        max_length=5,
        choices=POSITION_CHOICES,
        help_text="Whether user is going long or short"
    )
    price = models.FloatField(
        help_text="Price at which the trade was executed"
    )
    quantity = models.IntegerField(
        default=1,
        help_text="Number of units traded"
    )
    trade_time = models.DateTimeField(
        auto_now_add=True,
        help_text="When this trade was placed"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this trade was last updated"
    )
    
    class Meta:
        ordering = ['-trade_time']
        verbose_name = 'Trade'
        verbose_name_plural = 'Trades'
        # Ensure one position per user per market
        unique_together = ['market', 'user']
        indexes = [
            models.Index(fields=['market', 'position']),
            models.Index(fields=['user', 'trade_time']),
            models.Index(fields=['market', 'trade_time']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.position} on {self.market.premise[:30]}..."
    
    @property
    def is_long(self):
        """Check if this is a long position"""
        return self.position == 'LONG'
    
    @property
    def is_short(self):
        """Check if this is a short position"""
        return self.position == 'SHORT'
    
    @property
    def total_value(self):
        """Calculate total value of the trade"""
        return self.price * self.quantity
    
    def clean(self):
        """Validate the trade"""
        from django.core.exceptions import ValidationError
        
        # Check if market is open for trading
        if not self.market.is_trading_active:
            raise ValidationError("Market is not open for trading")
        
        # Check if user is verified (if profile exists)
        if hasattr(self.user, 'profile') and not self.user.profile.is_verified:
            raise ValidationError("Only verified users can place trades")
        
        # Validate price is within market spread
        if self.market.final_spread_low is not None and self.market.final_spread_high is not None:
            if self.position == 'LONG' and self.price < self.market.final_spread_high:
                raise ValidationError(f"Long position price must be at least {self.market.final_spread_high}")
            elif self.position == 'SHORT' and self.price > self.market.final_spread_low:
                raise ValidationError(f"Short position price must be at most {self.market.final_spread_low}")
        
        # Validate quantity
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
