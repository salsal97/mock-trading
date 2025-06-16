# Market Auto-Activation Feature

This document describes the automatic market activation functionality that selects winning spread bids when bidding windows close.

## Overview

The auto-activation feature automatically transitions markets from `CREATED` status to `OPEN` status when the spread bidding window closes. It selects the winning bid based on the tightest spread (lowest spread width) with earliest timestamp as a tie-breaker.

## How It Works

### 1. Winning Bid Selection

The system selects the winning bid using the following criteria:
- **Primary**: Lowest spread width (tightest spread)
- **Tie-breaker**: Earliest bid timestamp

### 2. Market Activation Process

When a market is activated:
1. **With Winning Bid**:
   - Sets `final_spread_low` and `final_spread_high` from the winning bid
   - Updates `created_by` to the winning bidder (they become the market maker)
   - Changes `status` to `OPEN`

2. **Without Bids**:
   - Sets `final_spread_low` to `50 - (initial_spread // 2)`
   - Sets `final_spread_high` to `50 + (initial_spread // 2)`
   - Keeps original `created_by` as market maker
   - Changes `status` to `OPEN`

### 3. Eligibility Criteria

A market is eligible for auto-activation when:
- `status` is `CREATED`
- Current time is past `spread_bidding_close`
- `final_spread_low` and `final_spread_high` are both `null`

## Implementation Methods

### 1. Lazy Evaluation (Automatic)

Markets are automatically activated when accessed through the API:
- **Market List**: `GET /api/market/`
- **Market Detail**: `GET /api/market/{id}/`
- **Market Stats**: `GET /api/market/stats/`

This ensures markets are activated as soon as users interact with the system after bidding closes.

### 2. Management Command (Manual/Scheduled)

Use the Django management command for batch processing:

```bash
# Dry run - see what would be activated
python manage.py auto_activate_markets --dry-run

# Activate all eligible markets
python manage.py auto_activate_markets

# Activate a specific market
python manage.py auto_activate_markets --market-id 123
```

### 3. Admin Interface

Administrators can:
- View auto-activation status in the admin list view
- Use bulk actions to activate selected markets
- See detailed bid information for each market
- Manually activate markets through the admin interface

### 4. API Endpoint (Admin Only)

Manual activation via API:
```bash
POST /api/market/{id}/manual_activate/
```

## Model Methods

### `Market.should_auto_activate`
Property that returns `True` if the market is eligible for auto-activation.

### `Market.auto_activate_market()`
Main activation method that:
- Validates eligibility
- Selects winning bid
- Updates market fields
- Returns detailed result dictionary

Example return value:
```python
{
    'success': True,
    'reason': 'Market activated with winning bid',
    'details': {
        'winning_bid': {
            'id': 123,
            'user': 'username',
            'spread_low': 45,
            'spread_high': 55,
            'spread_width': 10,
            'bid_time': '2024-01-01T12:00:00Z'
        },
        'final_spread_low': 45,
        'final_spread_high': 55,
        'market_maker': 'username'
    }
}
```

## Frontend Integration

### Admin Interface Features

1. **Auto-Activation Status**: Visual indicators show when markets are ready for activation
2. **Manual Activation Button**: Prominent button for eligible markets
3. **Activation Details**: Success messages show winning bid information
4. **Real-time Updates**: Interface refreshes after activation

### User Dashboard

Markets automatically show updated status and final spreads after activation through lazy evaluation.

## Scheduling (Optional)

For production environments, you can schedule the management command:

### Using Cron (Linux/Mac)
```bash
# Run every 5 minutes
*/5 * * * * /path/to/venv/bin/python /path/to/manage.py auto_activate_markets
```

### Using Windows Task Scheduler
Create a task that runs:
```cmd
C:\path\to\venv\Scripts\python.exe C:\path\to\manage.py auto_activate_markets
```

### Using Celery (Recommended for Django)
```python
# In your Celery tasks
@periodic_task(run_every=crontab(minute='*/5'))
def auto_activate_markets_task():
    call_command('auto_activate_markets')
```

## Testing

Comprehensive test suite covers:
- Basic auto-activation with winning bids
- No-bid scenarios
- Tie-breaking logic
- Eligibility validation
- API integration
- Lazy evaluation

Run tests:
```bash
python manage.py test market.tests.MarketAutoActivationTest
python manage.py test market.tests.MarketAutoActivationAPITest
```

## Logging

The system logs all activation events:
- Successful activations with details
- Failed activation attempts
- Lazy evaluation statistics

Check Django logs for auto-activation events.

## Security Considerations

- Only admin users can manually activate markets via API
- Lazy evaluation runs automatically for all authenticated users
- Management command requires server access
- All activations are logged for audit purposes

## Performance Notes

- Lazy evaluation adds minimal overhead to API calls
- Database queries are optimized with proper indexing
- Bulk activation via management command is efficient
- Admin interface shows activation status without extra queries

## Troubleshooting

### Common Issues

1. **Markets not activating**: Check eligibility criteria and timing
2. **No winning bid selected**: Verify bid data and spread calculations
3. **Permission errors**: Ensure proper admin permissions for manual activation
4. **Timing issues**: Verify server timezone settings

### Debug Commands

```bash
# Check eligible markets
python manage.py shell -c "
from market.models import Market
from django.utils import timezone
markets = Market.objects.filter(
    status='CREATED',
    spread_bidding_close__lt=timezone.now(),
    final_spread_low__isnull=True
)
print(f'Eligible markets: {markets.count()}')
for m in markets:
    print(f'Market {m.id}: {m.premise[:50]}...')
"

# Test activation for specific market
python manage.py shell -c "
from market.models import Market
market = Market.objects.get(id=YOUR_MARKET_ID)
result = market.auto_activate_market()
print(result)
"
```

## Future Enhancements

Potential improvements:
- Webhook notifications for activations
- Custom activation rules per market
- Integration with external trading systems
- Advanced bid selection algorithms
- Real-time WebSocket updates for activation events 