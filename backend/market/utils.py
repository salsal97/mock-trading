"""
Utility functions for market operations and common patterns
"""
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

def create_error_response(message, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Create a standardized error response
    """
    response_data = {'error': message}
    if errors:
        response_data['errors'] = errors
    return Response(response_data, status=status_code)

def create_success_response(message, data=None, status_code=status.HTTP_200_OK):
    """
    Create a standardized success response
    """
    response_data = {'message': message}
    if data:
        response_data.update(data)
    return Response(response_data, status=status_code)

def validate_market_timing(market_data):
    """
    Validate market timing constraints
    """
    errors = {}
    
    spread_bidding_open = market_data.get('spread_bidding_open')
    spread_bidding_close_trading_open = market_data.get('spread_bidding_close_trading_open')
    trading_close = market_data.get('trading_close')
    
    # Spread bidding timing
    if spread_bidding_open and spread_bidding_close_trading_open:
        if spread_bidding_open >= spread_bidding_close_trading_open:
            errors['spread_bidding_close_trading_open'] = 'Spread bidding close & trading open must be after spread bidding open'
    
    # Trading timing
    if spread_bidding_close_trading_open and trading_close:
        if spread_bidding_close_trading_open >= trading_close:
            errors['trading_close'] = 'Trading close must be after spread bidding close & trading open'
    
    return errors

def check_user_permissions(user, market=None, action='trade'):
    """
    Check if user has permission for specific market actions
    """
    if not user.is_authenticated:
        return False, "User must be authenticated"
    
    if not user.is_active:
        return False, "User account is inactive"
    
    # Check verification for trading actions
    if action in ['trade', 'spread_bid']:
        try:
            if not user.profile.is_verified:
                return False, "User must be verified to perform this action"
        except AttributeError:
            return False, "User profile not found"
    
    # Check market-specific permissions
    if market and action == 'trade':
        if market.created_by == user:
            return False, "Market creators cannot trade on their own markets"
    
    return True, "Permission granted"

def get_market_statistics(markets):
    """
    Calculate aggregate statistics for markets
    """
    stats = {
        'total_markets': len(markets),
        'markets_by_status': {},
        'total_trades': 0,
        'active_trading': 0
    }
    
    for market in markets:
        # Count by status
        status_key = market.status
        stats['markets_by_status'][status_key] = stats['markets_by_status'].get(status_key, 0) + 1
        
        # Count trades
        stats['total_trades'] += getattr(market, 'total_trades_count', 0)
        
        # Count active trading markets
        if market.is_trading_active:
            stats['active_trading'] += 1
    
    return stats

def log_market_action(market, user, action, details=None):
    """
    Log market actions for audit trail
    """
    log_message = f"Market {market.id} - {action} by {user.username}"
    if details:
        log_message += f" - {details}"
    
    logger.info(log_message)

def validate_trade_constraints(market, user, position, price, quantity):
    """
    Validate trade constraints and business rules
    """
    errors = {}
    
    # Check market is open for trading
    if not market.is_trading_active:
        errors['market'] = 'Market is not currently open for trading'
    
    # Check user permissions
    can_trade, reason = check_user_permissions(user, market, 'trade')
    if not can_trade:
        errors['user'] = reason
    
    # Validate price constraints based on position
    if market.final_spread_low is not None and market.final_spread_high is not None:
        if position == 'LONG' and price < market.final_spread_high:
            errors['price'] = f'Long position price must be >= {market.final_spread_high}'
        elif position == 'SHORT' and price > market.final_spread_low:
            errors['price'] = f'Short position price must be <= {market.final_spread_low}'
    
    # Validate quantity
    if quantity <= 0:
        errors['quantity'] = 'Quantity must be positive'
    
    return errors

def format_currency(amount):
    """
    Format currency amounts consistently
    """
    return f"${amount:.2f}" if amount is not None else "N/A"

def calculate_trade_value(price, quantity):
    """
    Calculate total trade value
    """
    return price * quantity if price and quantity else 0

def get_market_phase_display(market):
    """
    Get human-readable market phase
    """
    now = timezone.now()
    
    if market.status == 'CREATED':
        if market.is_spread_bidding_active:
            return 'Spread Bidding Active'
        else:
            return 'Spread Bidding Closed'
    elif market.status == 'OPEN':
        if market.is_trading_active:
            return 'Trading Active'
        else:
            return 'Trading Window Closed'
    elif market.status == 'CLOSED':
        return 'Awaiting Settlement'
    elif market.status == 'SETTLED':
        return 'Market Settled'
    
    return 'Unknown Phase' 