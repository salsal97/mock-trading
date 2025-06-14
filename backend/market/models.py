from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
