from django.core.management.base import BaseCommand
from market.lifecycle import maintain_markets


class Command(BaseCommand):
    help = 'Advance due market phases; safely repeat from a scheduler.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--market-id', type=int)

    def handle(self, *args, **options):
        result = maintain_markets(market_id=options['market_id'], dry_run=options['dry_run'])
        self.stdout.write(f"activated={result['activated']} delayed={result['delayed']} closed={result['closed']}")
