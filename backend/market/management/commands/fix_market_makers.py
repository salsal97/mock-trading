from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from market.models import Market
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Fix markets with missing or inconsistent market maker data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find OPEN markets without proper market maker setup
        broken_markets = Market.objects.filter(
            status='OPEN'
        ).filter(
            models.Q(market_maker__isnull=True) |
            models.Q(market_maker_spread_low__isnull=True) |
            models.Q(market_maker_spread_high__isnull=True) |
            models.Q(final_spread_low__isnull=True) |
            models.Q(final_spread_high__isnull=True)
        )
        
        if not broken_markets.exists():
            self.stdout.write(self.style.SUCCESS('No broken markets found!'))
            return
        
        self.stdout.write(f'Found {broken_markets.count()} markets with missing market maker data:')
        
        fixed_count = 0
        for market in broken_markets:
            self.stdout.write(f'\nMarket ID {market.id}: {market.premise[:50]}...')
            self.stdout.write(f'  Created by: {market.created_by.username}')
            self.stdout.write(f'  Market maker: {market.market_maker.username if market.market_maker else "None"}')
            self.stdout.write(f'  Final spread: {market.final_spread_low}-{market.final_spread_high}')
            self.stdout.write(f'  MM spread: {market.market_maker_spread_low}-{market.market_maker_spread_high}')
            
            if not dry_run:
                # Fix the market by setting proper market maker fields
                if not market.market_maker:
                    market.market_maker = market.created_by
                    self.stdout.write(f'  → Set market maker to {market.created_by.username}')
                
                if not market.market_maker_spread_low or not market.market_maker_spread_high:
                    if market.final_spread_low and market.final_spread_high:
                        market.market_maker_spread_low = market.final_spread_low
                        market.market_maker_spread_high = market.final_spread_high
                        self.stdout.write(f'  → Set MM spread to {market.final_spread_low}-{market.final_spread_high}')
                    else:
                        # Calculate from initial spread
                        market.final_spread_low = 50 - (market.initial_spread // 2)
                        market.final_spread_high = 50 + (market.initial_spread // 2)
                        market.market_maker_spread_low = market.final_spread_low
                        market.market_maker_spread_high = market.final_spread_high
                        self.stdout.write(f'  → Calculated spread from initial: {market.final_spread_low}-{market.final_spread_high}')
                
                if not market.final_spread_low or not market.final_spread_high:
                    market.final_spread_low = market.market_maker_spread_low
                    market.final_spread_high = market.market_maker_spread_high
                    self.stdout.write(f'  → Set final spread to {market.final_spread_low}-{market.final_spread_high}')
                
                market.save()
                fixed_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Fixed market {market.id}'))
            else:
                self.stdout.write('  → Would fix this market')
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\nDRY RUN: Would fix {broken_markets.count()} markets'))
            self.stdout.write('Run without --dry-run to apply fixes')
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Fixed {fixed_count} markets'))
            
        # Also check for markets that should be auto-activated
        eligible_markets = Market.objects.filter(
            status='CREATED',
            spread_bidding_close__lt=timezone.now(),
            final_spread_low__isnull=True,
            final_spread_high__isnull=True
        )
        
        if eligible_markets.exists():
            self.stdout.write(f'\nFound {eligible_markets.count()} markets eligible for auto-activation:')
            for market in eligible_markets:
                self.stdout.write(f'  Market ID {market.id}: {market.premise[:50]}...')
                if not dry_run:
                    result = market.auto_activate_market()
                    if result['success']:
                        self.stdout.write(self.style.SUCCESS(f'    ✓ Auto-activated: {result["reason"]}'))
                    else:
                        self.stdout.write(self.style.ERROR(f'    ✗ Failed: {result["reason"]}'))
                else:
                    self.stdout.write('    → Would auto-activate this market') 