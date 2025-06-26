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
    spread_bidding_close_trading_open = models.DateTimeField(
        help_text="When spread bidding closes and trading opens"
    )
    trading_close = models.DateTimeField(
        help_text="When trading closes"
    )
    outcome = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Final outcome of the market (set when settled)"
    )
    
    # Settlement fields
    final_outcome = models.BooleanField(null=True, blank=True, help_text="True if market resolves to YES/LONG, False if NO/SHORT")
    settlement_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Final settlement price")
    settled_at = models.DateTimeField(null=True, blank=True)
    market_maker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='market_maker_markets')
    market_maker_spread_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    market_maker_spread_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
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
        return self.spread_bidding_open <= now <= self.spread_bidding_close_trading_open
    
    @property
    def is_trading_active(self):
        """Check if trading is currently active"""
        now = timezone.now()
        return self.spread_bidding_close_trading_open <= now <= self.trading_close and self.status == 'OPEN'
    
    @property
    def can_be_settled(self):
        """Check if market can be settled"""
        now = timezone.now()
        return now > self.trading_close and self.status == 'CLOSED'
    
    @property
    def should_auto_activate(self):
        """
        Check if market should be automatically activated.
        Business rule: activate when:
        a. there has been at least one bid from one user and the spread bidding window is closed
        b. admin forcefully activates the market using their auto activate button
        """
        now = timezone.now()
        has_bids = self.spread_bids.exists()
        bidding_closed = now > self.spread_bidding_close_trading_open
        
        return (
            self.status == 'CREATED' and 
            bidding_closed and
            has_bids and
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
        
        # New rule: No default spread high, show that bids are needed
        return "No bids yet - waiting for initial bid"
    
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
        """Get the width of the current best spread bid, or None if no bids"""
        best_bid = self.best_spread_bid
        if best_bid:
            return best_bid.spread_width
        # New rule: No default spread, return None if no bids
        return None
    
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
        
        # Rule 7: Market maker cannot trade on their own market
        if self.market_maker == user:
            return False, "Market makers cannot trade on their own markets"
        
        # Rule 9: Admins cannot trade on markets
        if user.is_staff or user.is_superuser:
            return False, "Administrators cannot place trades"
        
        # Rule 9: Market creator cannot trade on their own market  
        if self.created_by == user:
            return False, "Market creators cannot trade on their own markets"
        
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
                        'bidding_closed': timezone.now() > self.spread_bidding_close_trading_open,
                        'has_bids': self.spread_bids.exists(),
                        'already_activated': self.final_spread_low is not None
                    }
                }
            
            # Get the winning bid - Rule 3: tie breaker is first come first serve
            winning_bid = self.best_spread_bid
            
            if not winning_bid:
                # This should not happen due to should_auto_activate check, but handle gracefully
                return {
                    'success': False,
                    'reason': 'No bids available for activation. Please place at least one spread bid before activation.',
                    'details': {
                        'bids_count': self.spread_bids.count(),
                        'requires_initial_bid': True
                    }
                }
            
            # Apply winning bid
            logger.info(f"Market {self.id}: Activating with winning bid from {winning_bid.user.username}")
            
            self.final_spread_low = winning_bid.spread_low
            self.final_spread_high = winning_bid.spread_high
            self.created_by = winning_bid.user  # Winner becomes the market maker
            
            # Set market maker fields for trading system
            self.market_maker = winning_bid.user
            self.market_maker_spread_low = winning_bid.spread_low
            self.market_maker_spread_high = winning_bid.spread_high
            
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
    
    def settle_market(self, outcome, settlement_price=None):
        """
        Settle the market and calculate all profit/loss for trades
        """
        if self.status == 'SETTLED':
            return False, "Market already settled"
            
        self.final_outcome = outcome
        self.settlement_price = settlement_price or (self.market_maker_spread_high if outcome else self.market_maker_spread_low)
        self.status = 'SETTLED'
        self.settled_at = timezone.now()
        self.save()
        
        # Calculate profit/loss for all trades
        trades = self.trade_set.all()
        for trade in trades:
            trade.calculate_settlement()
            
        return True, f"Market settled with outcome: {'YES' if outcome else 'NO'}"
    
    def auto_settle_if_time(self):
        """
        Check if market should be auto-settled based on trading_close time
        """
        if self.status == 'OPEN' and timezone.now() >= self.trading_close:
            self.status = 'CLOSED'
            self.save()
            # Auto-settlement logic could be added here based on business rules
            return True
        return False

    def save(self, *args, **kwargs):
        """Override save to ensure market maker fields are properly set"""
        from django.core.exceptions import ValidationError
        
        # If market is being set to OPEN status, ensure market maker fields are set
        if self.status == 'OPEN':
            if not self.market_maker:
                # If no market maker is set, use the market creator as default
                self.market_maker = self.created_by
                
            if not self.market_maker_spread_low or not self.market_maker_spread_high:
                # If market maker spread is not set, use final spread
                if self.final_spread_low and self.final_spread_high:
                    self.market_maker_spread_low = self.final_spread_low
                    self.market_maker_spread_high = self.final_spread_high
                else:
                    # New rule: No default spread, market should not be OPEN without actual bids
                    raise ValidationError("Cannot open market without final spread values from actual bids")
                    
            if not self.final_spread_low or not self.final_spread_high:
                # Ensure final spread is always set for OPEN markets
                self.final_spread_low = self.market_maker_spread_low
                self.final_spread_high = self.market_maker_spread_high
        
        super().save(*args, **kwargs)


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
        
        # Rule 5: Spread bid values should only be positive numbers
        if self.spread_low <= 0:
            raise ValidationError("Spread low must be a positive number")
        
        if self.spread_high <= 0:
            raise ValidationError("Spread high must be a positive number")
        
        if self.spread_low >= self.spread_high:
            raise ValidationError("Spread low must be less than spread high")
        
        if self.spread_width <= 0:
            raise ValidationError("Spread width must be positive")
        
        # Rule 2: You cannot bid outside the bidding windows
        if not self.market.is_spread_bidding_active:
            raise ValidationError("Spread bidding is not currently active for this market")
        
        # Rule 9: Admins cannot take part in bidding
        if self.user.is_staff or self.user.is_superuser:
            raise ValidationError("Administrators cannot place spread bids")
        
        # Rule 9: Market creator (admin) cannot bid on their own market
        if self.user == self.market.created_by:
            raise ValidationError("Market creators cannot bid on their own markets")
    
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
    
    # Settlement fields
    settlement_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(null=True, blank=True)
    
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
        
        # Rule 7: Market maker cannot place trades on their own market
        if self.user == self.market.market_maker:
            raise ValidationError("Market makers cannot trade on their own markets")
        
        # Rule 9: Admins cannot trade on markets
        if self.user.is_staff or self.user.is_superuser:
            raise ValidationError("Administrators cannot place trades")
        
        # Rule 9: Market creator cannot trade on their own market
        if self.user == self.market.created_by:
            raise ValidationError("Market creators cannot trade on their own markets")
        
        # Rule 7: Validate trading prices - buyers pay market maker HIGH, sellers pay market maker LOW
        if self.market.market_maker_spread_low is not None and self.market.market_maker_spread_high is not None:
            if self.position == 'LONG':
                # Buyers think market will settle above market maker HIGH, so they pay HIGH price
                expected_price = float(self.market.market_maker_spread_high)
                if abs(self.price - expected_price) > 0.01:  # Allow small floating point differences
                    raise ValidationError(f"Long positions must buy at market maker HIGH price: {expected_price}")
            elif self.position == 'SHORT':
                # Sellers think market will settle below market maker LOW, so they sell at LOW price  
                expected_price = float(self.market.market_maker_spread_low)
                if abs(self.price - expected_price) > 0.01:  # Allow small floating point differences
                    raise ValidationError(f"Short positions must sell at market maker LOW price: {expected_price}")
        
        # Validate quantity
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive")
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def calculate_settlement(self):
        """
        Calculate profit/loss for this trade based on market outcome
        """
        if self.is_settled or not self.market.final_outcome is not None:
            return
            
        market = self.market
        
        if self.position == 'LONG':
            # Long position: profit if market outcome is True (YES)
            if market.final_outcome:
                # Market resolved YES - LONG wins
                self.settlement_amount = self.quantity * market.settlement_price
                self.profit_loss = self.settlement_amount - (self.quantity * self.price)
            else:
                # Market resolved NO - LONG loses
                self.settlement_amount = 0
                self.profit_loss = -(self.quantity * self.price)
        else:  # SHORT position
            # Short position: profit if market outcome is False (NO)
            if not market.final_outcome:
                # Market resolved NO - SHORT wins
                self.settlement_amount = self.quantity * market.settlement_price
                self.profit_loss = self.settlement_amount - (self.quantity * self.price)
            else:
                # Market resolved YES - SHORT loses
                self.settlement_amount = 0
                self.profit_loss = -(self.quantity * self.price)
                
        self.is_settled = True
        self.settled_at = timezone.now()
        self.save()
        
        # Update user balance
        self.user.profile.balance += self.profit_loss
        self.user.profile.save()
