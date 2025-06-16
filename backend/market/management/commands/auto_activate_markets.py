from django.core.management.base import BaseCommand
from django.utils import timezone
from market.models import Market
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Automatically activate markets whose spread bidding window has closed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be activated without making changes',
        )
        parser.add_argument(
            '--market-id',
            type=int,
            help='Activate a specific market by ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        market_id = options.get('market_id')
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting auto-activation process (dry_run={dry_run})')
        )
        
        # Get markets that should be auto-activated
        if market_id:
            try:
                markets = [Market.objects.get(id=market_id)]
                self.stdout.write(f'Processing specific market ID: {market_id}')
            except Market.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Market with ID {market_id} not found')
                )
                return
        else:
            markets = Market.objects.filter(
                status='CREATED',
                spread_bidding_close__lt=timezone.now(),
                final_spread_low__isnull=True,
                final_spread_high__isnull=True
            )
            self.stdout.write(f'Found {markets.count()} markets eligible for auto-activation')
        
        activated_count = 0
        failed_count = 0
        
        for market in markets:
            self.stdout.write(f'\nProcessing Market ID {market.id}: "{market.premise[:50]}..."')
            
            if dry_run:
                # Show what would happen without making changes
                winning_bid = market.best_spread_bid
                if winning_bid:
                    self.stdout.write(
                        f'  Would activate with winning bid from {winning_bid.user.username} '
                        f'(spread: {winning_bid.spread_low}-{winning_bid.spread_high}, '
                        f'width: {winning_bid.spread_width})'
                    )
                else:
                    self.stdout.write(
                        f'  Would activate with initial spread (no bids received)'
                    )
                activated_count += 1
            else:
                # Actually activate the market
                result = market.auto_activate_market()
                
                if result['success']:
                    activated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {result["reason"]}')
                    )
                    
                    details = result['details']
                    if details.get('winning_bid'):
                        bid = details['winning_bid']
                        self.stdout.write(
                            f'    Winner: {bid["user"]} '
                            f'(spread: {bid["spread_low"]}-{bid["spread_high"]}, '
                            f'width: {bid["spread_width"]})'
                        )
                    
                    self.stdout.write(
                        f'    Final spread: {details["final_spread_low"]}-{details["final_spread_high"]}'
                    )
                    self.stdout.write(
                        f'    Market maker: {details["market_maker"]}'
                    )
                else:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ {result["reason"]}')
                    )
                    if 'error' in result['details']:
                        self.stdout.write(
                            self.style.ERROR(f'    Error: {result["details"]["error"]}')
                        )
        
        # Summary
        self.stdout.write(f'\n{"="*50}')
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN COMPLETE: {activated_count} markets would be activated'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'ACTIVATION COMPLETE: {activated_count} markets activated, {failed_count} failed'
                )
            )
        
        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Check logs for details on {failed_count} failed activations'
                )
            ) 