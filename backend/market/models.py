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
        """Display current spread - either initial or final range"""
        if self.final_spread_low is not None and self.final_spread_high is not None:
            return f"{self.final_spread_low} - {self.final_spread_high}"
        return str(self.initial_spread)
