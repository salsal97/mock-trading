from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Market

class MarketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test market with future dates
        now = timezone.now()
        self.market = Market.objects.create(
            premise="Will it rain tomorrow?",
            unit_price=1.0,
            initial_spread=50,
            created_by=self.user,
            spread_bidding_open=now + timedelta(hours=1),
            spread_bidding_close=now + timedelta(hours=2),
            trading_open=now + timedelta(hours=3),
            trading_close=now + timedelta(hours=24)
        )
    
    def test_market_creation(self):
        """Test that market is created correctly"""
        self.assertEqual(self.market.premise, "Will it rain tomorrow?")
        self.assertEqual(self.market.status, 'CREATED')
        self.assertEqual(self.market.created_by, self.user)
        self.assertEqual(self.market.initial_spread, 50)
        self.assertIsNone(self.market.outcome)
        self.assertIsNone(self.market.final_spread_low)
        self.assertIsNone(self.market.final_spread_high)
    
    def test_market_str_representation(self):
        """Test string representation of market"""
        expected = "Will it rain tomorrow?... - CREATED"
        self.assertEqual(str(self.market), expected)
    
    def test_current_spread_display_initial(self):
        """Test current spread display shows initial spread when no final spread set"""
        self.assertEqual(self.market.current_spread_display, "50")
    
    def test_current_spread_display_final(self):
        """Test current spread display shows final spread range when set"""
        self.market.final_spread_low = 40
        self.market.final_spread_high = 60
        self.market.save()
        self.assertEqual(self.market.current_spread_display, "40 - 60")
    
    def test_spread_bidding_active_property(self):
        """Test spread bidding active property"""
        # Should be False since spread bidding is in the future
        self.assertFalse(self.market.is_spread_bidding_active)
    
    def test_trading_active_property(self):
        """Test trading active property"""
        # Should be False since trading is in the future and status is CREATED
        self.assertFalse(self.market.is_trading_active)
    
    def test_can_be_settled_property(self):
        """Test can be settled property"""
        # Should be False since trading hasn't closed yet
        self.assertFalse(self.market.can_be_settled)
    
    def test_status_choices(self):
        """Test that all status choices are valid"""
        valid_statuses = ['CREATED', 'OPEN', 'CLOSED', 'SETTLED']
        for status in valid_statuses:
            self.market.status = status
            self.market.save()
            self.assertEqual(self.market.status, status)


class MarketViewSetTest(APITestCase):
    def setUp(self):
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create admin user
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        # Create test market
        now = timezone.now()
        self.market = Market.objects.create(
            premise="Test market premise",
            unit_price=1.0,
            initial_spread=50,
            created_by=self.admin_user,
            spread_bidding_open=now + timedelta(hours=1),
            spread_bidding_close=now + timedelta(hours=2),
            trading_open=now + timedelta(hours=3),
            trading_close=now + timedelta(hours=24)
        )
        
        self.client = APIClient()
    
    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access markets"""
        response = self.client.get('/api/market/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_authenticated_user_can_list_markets(self):
        """Test that authenticated users can list markets"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/market/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_authenticated_user_can_get_market_detail(self):
        """Test that authenticated users can get market details"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/market/{self.market.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['premise'], "Test market premise")
    
    def test_regular_user_cannot_create_market(self):
        """Test that regular users cannot create markets"""
        self.client.force_authenticate(user=self.user)
        market_data = {
            'premise': 'New market premise',
            'unit_price': 1.0,
            'initial_spread': 45,
            'spread_bidding_open': timezone.now() + timedelta(hours=1),
            'spread_bidding_close': timezone.now() + timedelta(hours=2),
            'trading_open': timezone.now() + timedelta(hours=3),
            'trading_close': timezone.now() + timedelta(hours=24)
        }
        response = self.client.post('/api/market/', market_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_user_can_create_market(self):
        """Test that admin users can create markets"""
        self.client.force_authenticate(user=self.admin_user)
        market_data = {
            'premise': 'New market premise',
            'unit_price': 1.0,
            'initial_spread': 45,
            'spread_bidding_open': (timezone.now() + timedelta(hours=1)).isoformat(),
            'spread_bidding_close': (timezone.now() + timedelta(hours=2)).isoformat(),
            'trading_open': (timezone.now() + timedelta(hours=3)).isoformat(),
            'trading_close': (timezone.now() + timedelta(hours=24)).isoformat()
        }
        response = self.client.post('/api/market/', market_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['premise'], 'New market premise')
        self.assertEqual(response.data['initial_spread'], 45)
        
        # Verify the market was created with the correct user
        created_market = Market.objects.get(premise='New market premise')
        self.assertEqual(created_market.created_by, self.admin_user)
    
    def test_market_timing_validation_rules(self):
        """Test that market timing validation rules are enforced"""
        self.client.force_authenticate(user=self.admin_user)
        base_time = timezone.now()
        
        # Test 1: Spread bidding close before spread bidding open
        invalid_data_1 = {
            'premise': 'Invalid timing test 1',
            'unit_price': 1.0,
            'initial_spread': 45,
            'spread_bidding_open': (base_time + timedelta(hours=2)).isoformat(),
            'spread_bidding_close': (base_time + timedelta(hours=1)).isoformat(),  # Before open
            'trading_open': (base_time + timedelta(hours=3)).isoformat(),
            'trading_close': (base_time + timedelta(hours=24)).isoformat()
        }
        response = self.client.post('/api/market/', invalid_data_1)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Spread bidding close must be after spread bidding open', str(response.data))
        
        # Test 2: Trading close before trading open
        invalid_data_2 = {
            'premise': 'Invalid timing test 2',
            'unit_price': 1.0,
            'initial_spread': 45,
            'spread_bidding_open': (base_time + timedelta(hours=1)).isoformat(),
            'spread_bidding_close': (base_time + timedelta(hours=2)).isoformat(),
            'trading_open': (base_time + timedelta(hours=24)).isoformat(),
            'trading_close': (base_time + timedelta(hours=3)).isoformat()  # Before open
        }
        response = self.client.post('/api/market/', invalid_data_2)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Trading close must be after trading open', str(response.data))
        
        # Test 3: Trading open before spread bidding close
        invalid_data_3 = {
            'premise': 'Invalid timing test 3',
            'unit_price': 1.0,
            'initial_spread': 45,
            'spread_bidding_open': (base_time + timedelta(hours=1)).isoformat(),
            'spread_bidding_close': (base_time + timedelta(hours=3)).isoformat(),
            'trading_open': (base_time + timedelta(hours=2)).isoformat(),  # Before spread close
            'trading_close': (base_time + timedelta(hours=24)).isoformat()
        }
        response = self.client.post('/api/market/', invalid_data_3)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Trading open must be after spread bidding close', str(response.data))
    
    def test_admin_can_set_final_spread(self):
        """Test that admin users can set final spread"""
        self.client.force_authenticate(user=self.admin_user)
        update_data = {
            'final_spread_low': 40,
            'final_spread_high': 60
        }
        response = self.client.patch(f'/api/market/{self.market.id}/', update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify the spread was updated
        self.market.refresh_from_db()
        self.assertEqual(self.market.final_spread_low, 40)
        self.assertEqual(self.market.final_spread_high, 60)
    
    def test_admin_user_can_access_stats(self):
        """Test that admin users can access market stats"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/market/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_markets', response.data)
        self.assertIn('markets_by_status', response.data)
    
    def test_regular_user_cannot_access_stats(self):
        """Test that regular users cannot access market stats"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/market/stats/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
