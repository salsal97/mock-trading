from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_UP
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
    settlement_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final settlement price (0.01 to 999999.99)"
    )
    settled_at = models.DateTimeField(null=True, blank=True)
    market_maker = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='market_maker_markets')
    market_maker_spread_low = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    market_maker_spread_high = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Settlement confirmation tracking
    settlement_preview_calculated = models.BooleanField(default=False, help_text="Whether settlement preview has been calculated")
    settlement_confirmed = models.BooleanField(default=False, help_text="Whether admin has confirmed the settlement")

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
        return self.status == 'CREATED' and self.spread_bidding_open <= now < self.spread_bidding_close_trading_open

    @property
    def is_trading_active(self):
        """Check if trading is currently active"""
        now = timezone.now()
        return self.spread_bidding_close_trading_open <= now < self.trading_close and self.status == 'OPEN'

    @property
    def can_be_settled(self):
        """Check if market can be settled - must be CLOSED and have settlement price"""
        return self.status == 'CLOSED' and self.settlement_price is not None

    @property
    def can_be_reopened(self):
        """Check if market can be reopened - must be CLOSED and not have settlement price entered"""
        return self.status == 'CLOSED' and self.settlement_price is None

    @property
    def should_delay_for_no_bids(self):
        """
        Check if market should be delayed due to no spread bids.
        New business rule: if there have been no bids made for the spread,
        even if the spread bidding window is closed, the trading will not open
        and the bidding close time will delay by a day (at a time),
        so will the trading close time.
        """
        now = timezone.now()
        has_no_bids = not self.spread_bids.exists()
        bidding_closed = now > self.spread_bidding_close_trading_open

        return (
            self.status == 'CREATED' and
            bidding_closed and
            has_no_bids and
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

        # Check if market should be delayed due to no bids
        if self.should_delay_for_no_bids:
            return "No bids - will delay by 1 day"

        # Default message for markets waiting for bids
        return "No bids yet - waiting for initial bid"

    @property
    def best_spread_bid(self):
        """Get the current best (tightest) spread bid"""
        latest = {}
        for bid in self.spread_bids.order_by('bid_time', 'id'):
            latest[bid.user_id] = bid
        bids = list(latest.values())
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
        return None

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
        except Trade.DoesNotExist:
            return None

    def can_user_trade(self, user):
        """Check if a user can place a trade on this market"""
        # Market must be open for trading
        if not self.is_trading_active:
            return False, "Market is not open for trading"

        if self.market_maker == user:
            return False, "Market makers cannot trade on their own markets"
        if self.created_by == user:
            return False, "Market creators cannot trade on their own markets"

        return True, "User can trade"

    def set_settlement_price(self, price):
        """Set settlement price and validate it - can be changed until settlement is confirmed"""
        if self.settlement_confirmed:
            raise ValidationError("Cannot change settlement price after settlement has been confirmed")

        if self.status != 'CLOSED':
            raise ValidationError("Can only set settlement price on CLOSED markets")

        # Validate settlement price range (0.01 to 999999.99)
        if not (Decimal('0.01') <= price <= Decimal('999999.99')):
            raise ValidationError("Settlement price must be between 0.01 and 999999.99")
        self.settlement_price = price.quantize(Decimal('0.01'), rounding=ROUND_UP)
        self.settlement_preview_calculated = False  # Reset preview flag
        self.settlement_confirmed = False  # Reset confirmation flag
        self.save()

        return self.settlement_price

    def reopen_trading(self, new_trading_close):
        """Reopen trading with new close time (admin only, only if not settled)"""
        if not self.can_be_reopened:
            raise ValidationError("Market cannot be reopened - either not closed or settlement already started")

        # Validate new trading close time
        if new_trading_close <= timezone.now():
            raise ValidationError("New trading close time must be in the future")

        if new_trading_close <= self.spread_bidding_close_trading_open:
            raise ValidationError("New trading close time must be after trading open time")

        self.status = 'OPEN'
        self.trading_close = new_trading_close
        self.settlement_price = None
        self.settlement_preview_calculated = False
        self.settlement_confirmed = False
        self.save()

        logger.info(f"Market {self.id} reopened for trading until {new_trading_close}")
        return True

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
        if self.spread_low <= 0:
            raise ValidationError("Spread low must be a positive number")

        if self.spread_high <= 0:
            raise ValidationError("Spread high must be a positive number")

        if self.spread_low >= self.spread_high:
            raise ValidationError("Spread low must be less than spread high")

        if self.spread_width <= 0:
            raise ValidationError("Spread width must be positive")
        if not self.market.is_spread_bidding_active:
            raise ValidationError("Spread bidding is not currently active for this market")
        # Global staff status does not determine market roles.
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

    def clean(self):
        """Validate the trade"""
        from django.core.exceptions import ValidationError
        # (trade will have settlement-related fields set)
        if not (self.is_settled or self.settlement_amount is not None or self.settled_at is not None):
            # Check if market is open for trading (only for new trades, not during settlement)
            if not self.market.is_trading_active:
                raise ValidationError("Market is not open for trading")
        if self.user == self.market.market_maker:
            raise ValidationError("Market makers cannot trade on their own markets")
        # Global staff status does not determine market roles.
        if self.user == self.market.created_by:
            raise ValidationError("Market creators cannot trade on their own markets")
        if self.market.market_maker_spread_low is not None and self.market.market_maker_spread_high is not None:
            if self.position == 'LONG':
                # Buyers think market will settle above market maker HIGH, so they pay HIGH price
                expected_price = float(self.market.market_maker_spread_high)
                if abs(float(self.price) - expected_price) > 0.01:  # Allow small floating point differences
                    raise ValidationError(f"Long positions must buy at market maker HIGH price: {expected_price}")
            elif self.position == 'SHORT':
                # Sellers think market will settle below market maker LOW, so they sell at LOW price
                expected_price = float(self.market.market_maker_spread_low)
                if abs(float(self.price) - expected_price) > 0.01:  # Allow small floating point differences
                    raise ValidationError(f"Short positions must sell at market maker LOW price: {expected_price}")
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive")

    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)

class SettlementEntry(models.Model):
    market = models.ForeignKey(Market, on_delete=models.PROTECT, related_name='settlement_entries')
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['market', 'user'], name='one_settlement_entry_per_user_market')]
