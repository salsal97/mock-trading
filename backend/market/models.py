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
        return self.spread_bidding_open <= now <= self.spread_bidding_close_trading_open
    
    @property
    def is_trading_active(self):
        """Check if trading is currently active"""
        now = timezone.now()
        return self.spread_bidding_close_trading_open <= now <= self.trading_close and self.status == 'OPEN'
    
    @property
    def should_auto_close(self):
        """Check if market should be automatically closed"""
        now = timezone.now()
        return self.status == 'OPEN' and now >= self.trading_close
    
    @property
    def can_be_settled(self):
        """Check if market can be settled - must be CLOSED and have settlement price"""
        return self.status == 'CLOSED' and self.settlement_price is not None
    
    @property
    def can_be_reopened(self):
        """Check if market can be reopened - must be CLOSED and not have settlement price entered"""
        return self.status == 'CLOSED' and self.settlement_price is None
    
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
    
    def delay_market_for_no_bids(self):
        """
        Delay the market by one day when there are no spread bids.
        
        This method:
        1. Extends spread_bidding_close_trading_open by 1 day
        2. Extends trading_close by 1 day
        3. Logs the delay action
        
        Returns:
            dict: Result of the delay with success status and details
        """
        try:
            if not self.should_delay_for_no_bids:
                return {
                    'success': False,
                    'reason': 'Market is not eligible for delay',
                    'details': {
                        'status': self.status,
                        'bidding_closed': timezone.now() > self.spread_bidding_close_trading_open,
                        'has_bids': self.spread_bids.exists(),
                        'already_activated': self.final_spread_low is not None
                    }
                }
            
            from datetime import timedelta
            
            # Store old times for logging
            old_bidding_close = self.spread_bidding_close_trading_open
            old_trading_close = self.trading_close
            
            # Delay both times by 24 hours
            self.spread_bidding_close_trading_open += timedelta(days=1)
            self.trading_close += timedelta(days=1)
            
            self.save()
            
            logger.info(f"Market {self.id}: Delayed by 1 day due to no spread bids")
            logger.info(f"Market {self.id}: Bidding close moved from {old_bidding_close} to {self.spread_bidding_close_trading_open}")
            logger.info(f"Market {self.id}: Trading close moved from {old_trading_close} to {self.trading_close}")
            
            return {
                'success': True,
                'reason': 'Market delayed by 1 day due to no spread bids',
                'details': {
                    'old_bidding_close': old_bidding_close,
                    'new_bidding_close': self.spread_bidding_close_trading_open,
                    'old_trading_close': old_trading_close,
                    'new_trading_close': self.trading_close,
                    'delay_hours': 24,
                    'bids_count': self.spread_bids.count()
                }
            }
            
        except Exception as e:
            logger.error(f"Error delaying market {self.id}: {str(e)}")
            return {
                'success': False,
                'reason': f'Error during delay: {str(e)}',
                'details': {'error': str(e)}
            }
    
    def auto_close_if_time(self):
        """Automatically close market if trading time has passed"""
        if self.should_auto_close:
            self.status = 'CLOSED'
            self.save()
            logger.info(f"Market {self.id} auto-closed at trading close time")
            return True
        return False

    def set_settlement_price(self, price):
        """Set settlement price and validate it"""
        if self.status != 'CLOSED':
            raise ValidationError("Can only set settlement price on CLOSED markets")
        
        if self.settlement_price is not None:
            raise ValidationError("Settlement price has already been set")
        
        # Validate settlement price range (0.01 to 999999.99)
        if not (Decimal('0.01') <= price <= Decimal('999999.99')):
            raise ValidationError("Settlement price must be between 0.01 and 999999.99")
        
        # Round to 2 decimal places, rounding up when necessary
        self.settlement_price = price.quantize(Decimal('0.01'), rounding=ROUND_UP)
        self.settlement_preview_calculated = False  # Reset preview flag
        self.settlement_confirmed = False  # Reset confirmation flag
        self.save()
        
        return self.settlement_price

    def calculate_settlement_preview(self):
        """Calculate settlement preview for all trades without updating balances"""
        if self.settlement_price is None:
            raise ValidationError("Settlement price must be set before calculating preview")
        
        trades = self.trades.all()
        settlement_data = {
            'market_id': self.id,
            'market_premise': self.premise,
            'settlement_price': self.settlement_price,
            'trades': [],
            'market_maker_impact': Decimal('0.00'),
            'total_trades': trades.count()
        }
        
        market_maker_total = Decimal('0.00')
        
        for trade in trades:
            # Calculate P&L according to new business rules
            if trade.position == 'LONG':
                # LONG: user is due (settlement_value - their_buy_value)
                trade_pnl = self.settlement_price - Decimal(str(trade.price))
            else:  # SHORT
                # SHORT: user pays (settlement_value - their_sell_value) 
                trade_pnl = Decimal(str(trade.price)) - self.settlement_price
            
            # Round to 2 decimal places
            trade_pnl = trade_pnl.quantize(Decimal('0.01'), rounding=ROUND_UP)
            
            # Market maker impact is opposite of trader P&L
            market_maker_total -= trade_pnl
            
            trade_data = {
                'trade_id': trade.id,
                'user_id': trade.user.id,
                'username': trade.user.username,
                'position': trade.position,
                'trade_price': Decimal(str(trade.price)),
                'settlement_price': self.settlement_price,
                'profit_loss': trade_pnl,
                'trade_time': trade.trade_time
            }
            settlement_data['trades'].append(trade_data)
        
        settlement_data['market_maker_impact'] = market_maker_total.quantize(Decimal('0.01'), rounding=ROUND_UP)
        settlement_data['market_maker'] = {
            'user_id': self.market_maker.id if self.market_maker else None,
            'username': self.market_maker.username if self.market_maker else 'Unknown'
        }
        
        self.settlement_preview_calculated = True
        self.save()
        
        return settlement_data

    def execute_settlement(self, confirmed_by_admin=True):
        """Execute final settlement and update all user balances"""
        if not self.settlement_preview_calculated:
            raise ValidationError("Must calculate settlement preview before executing")
        
        if not confirmed_by_admin:
            raise ValidationError("Admin confirmation required for settlement execution")
        
        if self.status == 'SETTLED':
            return {'success': False, 'message': 'Market already settled'}
        
        # Get settlement data
        settlement_data = self.calculate_settlement_preview()
        
        # Update user balances
        balance_updates = []
        
        for trade_data in settlement_data['trades']:
            user = User.objects.get(id=trade_data['user_id'])
            trade = Trade.objects.get(id=trade_data['trade_id'])
            
            # Update user balance
            if hasattr(user, 'profile'):
                old_balance = user.profile.balance
                user.profile.balance += trade_data['profit_loss']
                user.profile.save()
                
                balance_updates.append({
                    'user': user.username,
                    'old_balance': old_balance,
                    'new_balance': user.profile.balance,
                    'change': trade_data['profit_loss']
                })
            
            # Update trade settlement fields
            trade.settlement_amount = self.settlement_price
            trade.profit_loss = trade_data['profit_loss']
            trade.is_settled = True
            trade.settled_at = timezone.now()
            trade.save()
        
        # Update market maker balance
        if self.market_maker and hasattr(self.market_maker, 'profile'):
            old_mm_balance = self.market_maker.profile.balance
            self.market_maker.profile.balance += settlement_data['market_maker_impact']
            self.market_maker.profile.save()
            
            balance_updates.append({
                'user': f"{self.market_maker.username} (Market Maker)",
                'old_balance': old_mm_balance,
                'new_balance': self.market_maker.profile.balance,
                'change': settlement_data['market_maker_impact']
            })
        
        # Mark market as settled
        self.status = 'SETTLED'
        self.settled_at = timezone.now()
        self.settlement_confirmed = True
        self.save()
        
        logger.info(f"Market {self.id} settled successfully with {len(balance_updates)} balance updates")
        
        return {
            'success': True,
            'message': 'Market settled successfully',
            'settlement_data': settlement_data,
            'balance_updates': balance_updates
        }

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
    
    def auto_settle_if_time(self):
        """
        Check if market should be auto-closed based on trading_close time.
        Settlement is now a manual admin process after closing.
        """
        return self.auto_close_if_time()

    def save(self, *args, **kwargs):
        """Override save to ensure market maker fields are properly set"""
        # Auto-close market if time has passed
        if self.pk:  # Only for existing markets
            self.auto_close_if_time()
            
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
        Settlement calculation is now handled at the Market level.
        This method is kept for compatibility but redirects to market settlement.
        Use Market.calculate_settlement_preview() and Market.execute_settlement() instead.
        """
        if self.market.settlement_price is None:
            raise ValidationError("Market must have settlement price set before calculating trade settlement")
        
        if self.is_settled:
            return  # Already settled
            
        # Settlement is now handled through Market.execute_settlement()
        # This method should not be called directly
        logger.warning(f"Trade.calculate_settlement() called directly for trade {self.id}. "
                      f"Use Market.execute_settlement() instead for proper settlement flow.")
        return
