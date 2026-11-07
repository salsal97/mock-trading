from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Market

class RevivalLifecycleTest(TestCase):
    def test_lifecycle(self):
        admin = User.objects.create_user('owner', password='password')
        maker = User.objects.create_user('maker', password='password')
        trader = User.objects.create_user('trader', password='password')
        client = APIClient()
        def post(user, path, data, expected=200):
            client.force_authenticate(user)
            response = client.post(path, data, format='json')
            self.assertEqual(response.status_code, expected, response.data)
            return response
        now = timezone.now()
        market = post(admin, '/api/market/', {'premise':'Outcome?', 'unit_value':10,
            'spread_bidding_open':(now-timedelta(minutes=2)).isoformat(),
            'spread_bidding_close_trading_open':(now+timedelta(hours=1)).isoformat(),
            'trading_close':(now+timedelta(hours=2)).isoformat()}, 201).data
        self.assertIn('unit_value', market)
        self.assertNotIn('unit_price', market)
        self.assertNotIn('initial_spread', market)
        base = '/api/market/%s/' % market['id']
        post(maker, base+'place_spread_bid/', {'spread_low':85,'spread_high':95}, 201)
        post(trader, base+'place_spread_bid/', {'spread_low':80,'spread_high':100}, 201)
        post(maker, base+'place_spread_bid/', {'spread_low':70,'spread_high':110}, 201)
        client.force_authenticate(maker)
        ranking = client.get('/api/market/').data[0]
        self.assertEqual(ranking['personal_rank'], 2)
        self.assertEqual([q['user_username'] for q in ranking['top_quotes']], ['trader', 'maker'])
        post(maker, base+'manual_activate/', {}, 403)
        post(admin, base+'manual_activate/', {})
        m = Market.objects.get(pk=market['id'])
        self.assertEqual(m.market_maker, trader)
        self.assertEqual(m.created_by, admin)
        post(admin, base+'place_trade/', {'position':'BUY'}, 400)
        post(trader, base+'place_trade/', {'position':'BUY'}, 400)
        post(maker, base+'place_trade/', {'position':'LONG'}, 400)
        post(maker, base+'place_trade/', {'position':'BUY', 'quantity': 1}, 400)
        post(maker, base+'place_trade/', {'position':'BUY'})
        post(maker, base+'place_trade/', {'position':'SELL'})
        client.force_authenticate(maker)
        activity = client.get(base+'trades/')
        self.assertEqual(activity.status_code, 200, activity.data)
        self.assertEqual(activity.data['trades'][0]['position'], 'SELL')
        self.assertNotIn('quantity', activity.data['trades'][0])
        self.assertEqual(client.get('/api/market/').data[0]['user_trade']['position'], 'SELL')
        self.assertEqual(maker.profile.balance, Decimal('1000'))
        post(admin, base+'close-trading/', {})
        post(maker, base+'place_trade/', {'position':'BUY'}, 400)
        post(admin, base+'set-settlement-price/', {'price':'90'})
        client.force_authenticate(admin)
        response = client.get(base+'settlement-preview/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['trades'][0]['position'], 'SELL')
        old_token = response.data['preview_version']
        client.force_authenticate(admin)
        edit = client.patch(base+'edit/', {'unit_value': 20}, format='json')
        self.assertEqual(edit.status_code, 200, edit.data)
        post(admin, base+'execute-settlement/', {'confirmed':True}, 400)
        preview = client.get(base+'settlement-preview/')
        self.assertEqual(preview.status_code, 200, preview.data)
        token = preview.data['preview_version']
        self.assertNotEqual(old_token, token)
        post(admin, base+'execute-settlement/', {'confirmed': True, 'preview_version': old_token}, 400)
        with patch('market.models.SettlementEntry.objects.create', side_effect=RuntimeError('injected failure')):
            post(admin, base+'execute-settlement/', {'confirmed':True, 'preview_version':token}, 500)
        maker.profile.refresh_from_db(); trader.profile.refresh_from_db()
        self.assertEqual(maker.profile.balance, Decimal('1000'))
        self.assertEqual(trader.profile.balance, Decimal('1000'))
        m.refresh_from_db(); self.assertFalse(m.settlement_confirmed)
        post(admin, base+'execute-settlement/', {'confirmed':True, 'preview_version':token})
        maker.profile.refresh_from_db(); trader.profile.refresh_from_db()
        self.assertEqual(maker.profile.balance, Decimal('800'))
        self.assertEqual(trader.profile.balance, Decimal('1200'))
        post(admin, base+'execute-settlement/', {'confirmed':True, 'preview_version':token}, 400)
        maker.profile.refresh_from_db(); self.assertEqual(maker.profile.balance, Decimal('800'))
        settled = client.get(base+'settled-trades/')
        self.assertEqual(settled.status_code, 200, settled.data)
        self.assertEqual(settled.data['trades'][0]['position'], 'SELL')
        self.assertNotIn('quantity', settled.data['trades'][0])

        self.assertEqual(m.settlement_entries.count(), 2)
    def test_overflow_preview_is_rejected_without_balance_changes(self):
        now = timezone.now()
        owner = User.objects.create_user('large_owner')
        maker = User.objects.create_user('large_maker')
        trader = User.objects.create_user('large_trader')
        market = Market.objects.create(premise='Large values', unit_price=99999999, initial_spread=1,
            created_by=owner, spread_bidding_open=now-timedelta(hours=2),
            spread_bidding_close_trading_open=now-timedelta(hours=1), trading_close=now+timedelta(hours=1),
            status='OPEN', market_maker=maker, final_spread_low=80, final_spread_high=90,
            market_maker_spread_low=80, market_maker_spread_high=90)
        client = APIClient(); client.force_authenticate(trader)
        response = client.post(f'/api/market/{market.id}/place_trade/', {'position':'BUY'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        client.force_authenticate(owner)
        for endpoint, data in [('close-trading/', {}), ('set-settlement-price/', {'price':'999999.99'})]:
            response = client.post(f'/api/market/{market.id}/{endpoint}', data, format='json')
            self.assertEqual(response.status_code, 200, response.data)
        response = client.get(f'/api/market/{market.id}/settlement-preview/')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('supported range', str(response.data))
        trader.profile.refresh_from_db(); maker.profile.refresh_from_db(); market.refresh_from_db()
        self.assertEqual(trader.profile.balance, Decimal('1000'))
        self.assertEqual(maker.profile.balance, Decimal('1000'))
        self.assertFalse(market.settlement_preview_calculated)
        self.assertFalse(market.settlement_entries.exists())
