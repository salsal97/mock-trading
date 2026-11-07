from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from .models import Market


def maintain_markets(now=None, market_id=None, dry_run=False):
    """Advance due markets under a market row lock; safe to run repeatedly."""
    now = now or timezone.now()
    counts = {'activated': 0, 'delayed': 0, 'closed': 0}
    ids = Market.objects.filter(status__in=['CREATED', 'OPEN']).order_by('id')
    if market_id is not None:
        ids = ids.filter(pk=market_id)
    for pk in list(ids.values_list('pk', flat=True)):
        with transaction.atomic():
            market = Market.objects.select_for_update().get(pk=pk)
            if market.status == 'CREATED' and market.spread_bidding_close_trading_open <= now:
                bid = market.best_spread_bid
                if bid:
                    counts['activated'] += 1
                    if not dry_run:
                        market.final_spread_low = bid.spread_low
                        market.final_spread_high = bid.spread_high
                        market.market_maker = bid.user
                        market.market_maker_spread_low = bid.spread_low
                        market.market_maker_spread_high = bid.spread_high
                        market.status = 'OPEN'
                        market.save()
                else:
                    counts['delayed'] += 1
                    if not dry_run:
                        days = (now - market.spread_bidding_close_trading_open).days + 1
                        market.spread_bidding_close_trading_open += timedelta(days=days)
                        market.trading_close += timedelta(days=days)
                        market.save()
            if market.status == 'OPEN' and market.trading_close <= now:
                counts['closed'] += 1
                if not dry_run:
                    market.status = 'CLOSED'
                    market.save()
    return counts
