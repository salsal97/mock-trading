import hashlib
import json
import logging
from decimal import Decimal, ROUND_UP

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import UserProfile
from .models import Market, SettlementEntry, Trade

logger = logging.getLogger(__name__)


def position_profit_loss(position, entry_price, outcome, unit_value):
    """Calculate one unit using stored LONG/SHORT names and round away from zero."""
    entry = Decimal(str(entry_price))
    change = outcome - entry if position == 'LONG' else entry - outcome
    return (change * Decimal(str(unit_value))).quantize(Decimal('0.01'), rounding=ROUND_UP)


def validate_settlement_limits(market, data, profiles=None):
    """Reject results that cannot fit in the existing balance and trade fields."""
    amounts = {item['user_id']: item['profit_loss'] for item in data['trades']}
    amounts[market.market_maker_id] = data['market_maker_impact']
    if profiles is None:
        profiles = {p.user_id: p for p in UserProfile.objects.filter(user_id__in=amounts)}
    if len(profiles) != len(amounts):
        raise ValidationError('Missing participant profile')
    maximum = Decimal('99999999.99')  # UserProfile.balance and Trade.profit_loss
    for user_id, amount in amounts.items():
        if abs(amount) > maximum or abs(profiles[user_id].balance + amount) > maximum:
            raise ValidationError('Settlement result or resulting balance exceeds the supported range')

def settlement_preview_version(market):
    """Identify the exact preview, including the last market edit/preview event."""
    positions = list(market.trades.order_by('id').values_list('id', 'user_id', 'position', 'price'))
    payload = [market.pk, str(market.settlement_price), str(Decimal(str(market.unit_price)).quantize(Decimal('0.01'))), market.market_maker_id,
               market.updated_at.isoformat(), positions]
    return hashlib.sha256(json.dumps(payload, separators=(',', ':')).encode('utf-8')).hexdigest()

def calculate_settlement_preview(market):
    """Calculate settlement preview for all trades without updating balances"""
    if market.status != 'CLOSED' or market.settlement_confirmed or not market.market_maker_id:
        raise ValidationError('A closed, unconfirmed market with a maker is required')
    if market.settlement_price is None:
        raise ValidationError("Settlement price must be set before calculating preview")

    trades = market.trades.all()
    settlement_data = {
        'market_id': market.id,
        'market_premise': market.premise,
        'settlement_price': market.settlement_price,
        'trades': [],
        'market_maker_impact': Decimal('0.00'),
        'total_trades': trades.count()
    }

    market_maker_total = Decimal('0.00')

    for trade in trades:
        trade_pnl = position_profit_loss(trade.position, trade.price, market.settlement_price, market.unit_price)
        market_maker_total -= trade_pnl

        trade_data = {
            'trade_id': trade.id,
            'user_id': trade.user.id,
            'username': trade.user.username,
            'position': 'BUY' if trade.position == 'LONG' else 'SELL',
            'trade_price': Decimal(str(trade.price)),
            'settlement_price': market.settlement_price,
            'profit_loss': trade_pnl,
            'trade_time': trade.trade_time
        }
        settlement_data['trades'].append(trade_data)

    settlement_data['market_maker_impact'] = market_maker_total.quantize(Decimal('0.01'), rounding=ROUND_UP)
    settlement_data['market_maker'] = {
        'user_id': market.market_maker.id if market.market_maker else None,
        'username': market.market_maker.username if market.market_maker else 'Unknown'
    }

    validate_settlement_limits(market, settlement_data)
    market.settlement_preview_calculated = True
    market.save()
    # Saving changes updated_at, so generate the token only after the preview is recorded.
    settlement_data['preview_version'] = settlement_preview_version(market)

    return settlement_data

def execute_settlement(market, confirmed_by_admin=True, preview_version=None):
    """Lock the market, validate the preview, then atomically record all results."""
    with transaction.atomic():
        market = Market.objects.select_for_update().get(pk=market.pk)
        if market.status != 'CLOSED' or market.settlement_confirmed or not market.market_maker_id:
            return {'success': False, 'message': 'Market is not eligible for settlement'}
        if not market.settlement_preview_calculated:
            raise ValidationError("Must calculate settlement preview before executing")

        if not confirmed_by_admin:
            raise ValidationError("Admin confirmation required for settlement execution")

        # Validate before recalculating: calculation records a new preview and changes its token.
        if not isinstance(preview_version, str) or preview_version != settlement_preview_version(market):
            raise ValidationError('Settlement preview is stale; review a new preview')
        settlement_data = calculate_settlement_preview(market)

        user_ids = [t['user_id'] for t in settlement_data['trades']]
        if market.market_maker_id:
            user_ids.append(market.market_maker_id)
        # A stable lock order prevents deadlocks when concurrent markets share participants.
        profiles = {p.user_id: p for p in UserProfile.objects.select_for_update().filter(user_id__in=user_ids).order_by('user_id')}
        if len(profiles) != len(set(user_ids)):
            raise ValidationError('Missing participant profile')
        validate_settlement_limits(market, settlement_data, profiles)
        balance_updates = []

        # Balances, ledger entries, trade results and market status share this transaction.
        for trade_data in settlement_data['trades']:
            user = User.objects.get(id=trade_data['user_id'])
            profile = profiles[user.id]
            trade = Trade.objects.get(id=trade_data['trade_id'])
            if hasattr(user, 'profile'):
                old_balance = profile.balance
                profile.balance += trade_data['profit_loss']
                profile.save()
                SettlementEntry.objects.create(market=market, user=user, amount=trade_data['profit_loss'])

                balance_updates.append({
                    'user': user.username,
                    'old_balance': old_balance,
                    'new_balance': profile.balance,
                    'change': trade_data['profit_loss']
                })
            trade.settlement_amount = market.settlement_price
            trade.profit_loss = trade_data['profit_loss']
            trade.is_settled = True
            trade.settled_at = timezone.now()
            trade.save()
        if market.market_maker and hasattr(market.market_maker, 'profile'):
            maker_profile = profiles[market.market_maker_id]
            old_mm_balance = maker_profile.balance
            maker_profile.balance += settlement_data['market_maker_impact']
            maker_profile.save()
            SettlementEntry.objects.create(market=market, user=market.market_maker, amount=settlement_data['market_maker_impact'])

            balance_updates.append({
                'user': f"{market.market_maker.username} (Market Maker)",
                'old_balance': old_mm_balance,
                'new_balance': maker_profile.balance,
                'change': settlement_data['market_maker_impact']
            })
        market.status = 'SETTLED'
        market.settled_at = timezone.now()
        market.settlement_confirmed = True
        market.save()

        logger.info(f"Market {market.id} settled successfully with {len(balance_updates)} balance updates")

        return {
            'success': True,
            'message': 'Market settled successfully',
            'settlement_data': settlement_data,
            'balance_updates': balance_updates
        }

