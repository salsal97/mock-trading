from datetime import timedelta
from io import StringIO
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Market, SpreadBid

class MaintenanceTest(TestCase):
    def test_command_advances_due_markets_once(self):
        now = timezone.now()
        owner = User.objects.create_user('owner')
        bidder = User.objects.create_user('bidder')
        def market(name):
            return Market.objects.create(premise=name, created_by=owner, unit_price=10, initial_spread=5,
                spread_bidding_open=now-timedelta(days=3), spread_bidding_close_trading_open=now+timedelta(hours=1),
                trading_close=now+timedelta(hours=2))
        empty, quoted, closed = market('empty'), market('quoted'), market('closed')
        SpreadBid.objects.create(market=quoted, user=bidder, spread_low=80, spread_high=100)
        Market.objects.filter(pk__in=[empty.pk, quoted.pk]).update(spread_bidding_close_trading_open=now-timedelta(hours=1))
        Market.objects.filter(pk=closed.pk).update(status='OPEN', market_maker=bidder, final_spread_low=80,
            final_spread_high=100, market_maker_spread_low=80, market_maker_spread_high=100,
            trading_close=now-timedelta(minutes=1))
        out = StringIO(); call_command('maintain_markets', stdout=out)
        empty.refresh_from_db(); quoted.refresh_from_db(); closed.refresh_from_db()
        self.assertGreater(empty.spread_bidding_close_trading_open, now)
        self.assertEqual(quoted.market_maker, bidder); self.assertEqual(quoted.created_by, owner)
        self.assertEqual(quoted.status, 'OPEN'); self.assertEqual(closed.status, 'CLOSED')
        deadline = empty.spread_bidding_close_trading_open
        out = StringIO(); call_command('maintain_markets', stdout=out)
        empty.refresh_from_db(); self.assertEqual(empty.spread_bidding_close_trading_open, deadline)
        self.assertIn('activated=0 delayed=0 closed=0', out.getvalue())

class GuardTests(TestCase):
    def test_invalid_numbers_and_legacy_mutations(self):
        owner = User.objects.create_user('owner', is_staff=True)
        other = User.objects.create_user('other')
        now = timezone.now()
        m = Market.objects.create(premise='Test', unit_price=10, initial_spread=1, created_by=owner,
            spread_bidding_open=now-timedelta(hours=1), spread_bidding_close_trading_open=now+timedelta(hours=1),
            trading_close=now+timedelta(hours=2))
        c = APIClient(); c.force_authenticate(owner)
        base = f'/api/market/{m.id}/'
        self.assertEqual(c.patch(base, {'status': 'SETTLED'}, format='json').status_code, 405)
        self.assertEqual(c.patch(base+'edit/', {'unit_value': 'NaN'}, format='json').status_code, 400)
        self.assertEqual(c.post(base+'place_trade/', {'position': []}, format='json').status_code, 400)
        self.assertEqual(c.get('/api/market/positions/').status_code, 404)
        m.status = 'CLOSED'; m.settlement_preview_calculated = True; m.save()
        self.assertEqual(c.post(base+'execute-settlement/', {'confirmed':True}, format='json').status_code, 400)
        self.assertEqual(c.post(base+'set-settlement-price/', {'price':'NaN'}, format='json').status_code, 400)
        self.assertEqual(c.post('/api/market/999999/close-trading/', {}, format='json').status_code, 404)
    def test_four_quotes_show_three_and_personal_rank(self):
        owner = User.objects.create_user('rank_owner')
        users = [User.objects.create_user(f'rank_{i}') for i in range(4)]
        now = timezone.now()
        m = Market.objects.create(premise='Ranking', unit_price=10, initial_spread=1, created_by=owner,
            spread_bidding_open=now-timedelta(hours=1), spread_bidding_close_trading_open=now+timedelta(hours=1),
            trading_close=now+timedelta(hours=2))
        c = APIClient()
        for i, user in enumerate(users):
            c.force_authenticate(user)
            response = c.post(f'/api/market/{m.pk}/place_spread_bid/', {'spread_low': 80, 'spread_high': 90+i}, format='json')
            self.assertEqual(response.status_code, 201, response.data)
        response = c.get('/api/market/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0]['personal_rank'], 4)
        self.assertEqual([item['user_username'] for item in response.data[0]['top_quotes']], ['rank_0', 'rank_1', 'rank_2'])
        c.force_authenticate(users[0])
        response = c.post(f'/api/market/{m.pk}/place_spread_bid/', {'spread_low': 70, 'spread_high': 120}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        response = c.get('/api/market/')
        self.assertEqual(response.data[0]['personal_rank'], 4)
        self.assertEqual([item['user_username'] for item in response.data[0]['top_quotes']], ['rank_1', 'rank_2', 'rank_3'])
