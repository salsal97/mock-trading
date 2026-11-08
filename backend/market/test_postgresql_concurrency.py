"""Optional PostgreSQL locking checks, only with an explicitly isolated test database."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest import skipUnless
from django.contrib.auth.models import User
from django.db import connection, close_old_connections
from django.test import TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Market, Trade, SettlementEntry
from .settlement import calculate_settlement_preview

@skipUnless(connection.vendor == 'postgresql', 'Requires isolated PostgreSQL for row-lock tests')
class PostgreSQLSettlementConcurrencyTest(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user('concurrency_owner')
        self.maker = User.objects.create_user('concurrency_maker')
        self.trader = User.objects.create_user('concurrency_trader')

    def make_preview(self, name):
        now = timezone.now()
        market = Market.objects.create(premise=name, created_by=self.owner, unit_price=10, initial_spread=1,
            status='OPEN', market_maker=self.maker, final_spread_low=80, final_spread_high=90,
            market_maker_spread_low=80, market_maker_spread_high=90,
            spread_bidding_open=now-timedelta(hours=2), spread_bidding_close_trading_open=now-timedelta(hours=1),
            trading_close=now+timedelta(hours=1))
        Trade.objects.create(user=self.trader, market=market, position='LONG', price=90, quantity=1)
        market.status = 'CLOSED'; market.save(); market.set_settlement_price(Decimal('93'))
        return market, calculate_settlement_preview(market)['preview_version']

    def submit_simultaneously(self, requests):
        barrier = Barrier(len(requests))
        def submit(item):
            close_old_connections()
            try:
                client = APIClient(); client.force_authenticate(user=User.objects.get(pk=self.owner.pk))
                barrier.wait(timeout=10)
                response = client.post(f'/api/market/{item[0]}/execute-settlement/',
                    {'confirmed':True, 'preview_version':item[1]}, format='json')
                return response.status_code, response.data
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=len(requests)) as pool:
            return list(pool.map(submit, requests))

    def test_duplicate_confirmation_applies_once(self):
        market, token = self.make_preview('duplicate')
        results = self.submit_simultaneously([(market.pk, token)] * 2)
        self.assertEqual(sorted(code for code, _ in results), [200, 400], results)
        self.trader.profile.refresh_from_db(); self.maker.profile.refresh_from_db()
        self.assertEqual(self.trader.profile.balance, Decimal('1030'))
        self.assertEqual(self.maker.profile.balance, Decimal('970'))
        self.assertEqual(SettlementEntry.objects.filter(market=market).count(), 2)

    def test_parallel_markets_update_shared_balances(self):
        a, ta = self.make_preview('market A'); b, tb = self.make_preview('market B')
        results = self.submit_simultaneously([(a.pk,ta), (b.pk,tb)])
        self.assertEqual([code for code, _ in results], [200, 200], results)
        self.trader.profile.refresh_from_db(); self.maker.profile.refresh_from_db()
        self.assertEqual(self.trader.profile.balance, Decimal('1060'))
        self.assertEqual(self.maker.profile.balance, Decimal('940'))
        self.assertEqual(SettlementEntry.objects.count(), 4)
