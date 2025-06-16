from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from .models import Market, SpreadBid
from accounts.models import UserProfile

class MarketModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        # Set user as verified through profile
        self.user.profile.is_verified = True
        self.user.profile.save()
        
        # Create a market with timing in the future
        now = timezone.now()
        self.market = Market.objects.create(
            premise="Test market premise",
            unit_price=1.0,
            initial_spread=10,
            created_by=self.user,
            spread_bidding_open=now + timedelta(hours=1),
            spread_bidding_close=now + timedelta(hours=2),
            trading_open=now + timedelta(hours=3),
            trading_close=now + timedelta(hours=4)
        )

    def test_market_creation(self):
        """Test basic market creation"""
        self.assertEqual(self.market.premise, "Test market premise")
        self.assertEqual(self.market.status, 'CREATED')
        self.assertEqual(self.market.initial_spread, 10)
        self.assertEqual(self.market.current_best_spread_width, 10)

    def test_market_spread_bidding_properties(self):
        """Test market spread bidding properties"""
        # Initially no bids
        self.assertIsNone(self.market.best_spread_bid)
        self.assertEqual(self.market.current_best_spread_width, 10)
        
        # Create a spread bid
        bid = SpreadBid.objects.create(
            market=self.market,
            user=self.user,
            spread_low=45,
            spread_high=55
        )
        
        # Check best bid
        self.assertEqual(self.market.best_spread_bid, bid)
        self.assertEqual(self.market.current_best_spread_width, 10)  # bid width = 55-45 = 10

    def test_market_timing_properties(self):
        """Test market timing properties"""
        # Initially not active (times are in future)
        self.assertFalse(self.market.is_spread_bidding_active)
        self.assertFalse(self.market.is_trading_active)
        self.assertFalse(self.market.can_be_settled)


class MarketAutoActivationTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user1.profile.is_verified = True
        self.user1.profile.save()
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.user2.profile.is_verified = True
        self.user2.profile.save()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        # Create a market with bidding window that has closed
        now = timezone.now()
        self.market = Market.objects.create(
            premise="Test market for auto-activation",
            unit_price=1.0,
            initial_spread=20,
            created_by=self.admin_user,
            spread_bidding_open=now - timedelta(hours=2),
            spread_bidding_close=now - timedelta(hours=1),  # Closed 1 hour ago
            trading_open=now + timedelta(hours=1),
            trading_close=now + timedelta(hours=3)
        )

    def test_should_auto_activate_property(self):
        """Test the should_auto_activate property"""
        # Market should be eligible for auto-activation
        self.assertTrue(self.market.should_auto_activate)
        
        # After activation, should not be eligible anymore
        self.market.auto_activate_market()
        self.assertFalse(self.market.should_auto_activate)

    def test_auto_activate_with_winning_bid(self):
        """Test auto-activation with a winning bid"""
        # Create multiple bids
        bid1 = SpreadBid.objects.create(
            market=self.market,
            user=self.user1,
            spread_low=40,
            spread_high=60  # width = 20
        )
        
        bid2 = SpreadBid.objects.create(
            market=self.market,
            user=self.user2,
            spread_low=45,
            spread_high=55  # width = 10 (better)
        )
        
        # Auto-activate the market
        result = self.market.auto_activate_market()
        
        # Check result
        self.assertTrue(result['success'])
        self.assertEqual(result['reason'], 'Market activated with winning bid')
        
        # Check market state
        self.market.refresh_from_db()
        self.assertEqual(self.market.status, 'OPEN')
        self.assertEqual(self.market.final_spread_low, 45)
        self.assertEqual(self.market.final_spread_high, 55)
        self.assertEqual(self.market.created_by, self.user2)  # Winner becomes market maker
        
        # Check result details
        details = result['details']
        self.assertEqual(details['winning_bid']['user'], 'user2')
        self.assertEqual(details['winning_bid']['spread_width'], 10)
        self.assertEqual(details['market_maker'], 'user2')

    def test_auto_activate_with_no_bids(self):
        """Test auto-activation when no bids are received"""
        # Auto-activate the market without any bids
        result = self.market.auto_activate_market()
        
        # Check result
        self.assertTrue(result['success'])
        self.assertEqual(result['reason'], 'No bids received, activated with initial spread')
        
        # Check market state
        self.market.refresh_from_db()
        self.assertEqual(self.market.status, 'OPEN')
        self.assertEqual(self.market.final_spread_low, 40)  # 50 - (20//2)
        self.assertEqual(self.market.final_spread_high, 60)  # 50 + (20//2)
        self.assertEqual(self.market.created_by, self.admin_user)  # Original creator remains
        
        # Check result details
        details = result['details']
        self.assertIsNone(details['winning_bid'])
        self.assertEqual(details['market_maker'], 'admin')

    def test_auto_activate_tie_breaker(self):
        """Test that earliest bid wins in case of tie"""
        # Create two bids with same spread width
        bid1 = SpreadBid.objects.create(
            market=self.market,
            user=self.user1,
            spread_low=45,
            spread_high=55  # width = 10
        )
        
        # Wait a moment to ensure different timestamps
        import time
        time.sleep(0.01)
        
        bid2 = SpreadBid.objects.create(
            market=self.market,
            user=self.user2,
            spread_low=40,
            spread_high=50  # width = 10 (same as bid1)
        )
        
        # Auto-activate the market
        result = self.market.auto_activate_market()
        
        # Check that the earlier bid (bid1) won
        self.assertTrue(result['success'])
        self.market.refresh_from_db()
        self.assertEqual(self.market.created_by, self.user1)  # First bidder wins
        self.assertEqual(self.market.final_spread_low, 45)
        self.assertEqual(self.market.final_spread_high, 55)

    def test_auto_activate_not_eligible(self):
        """Test auto-activation when market is not eligible"""
        # Market with bidding still active
        now = timezone.now()
        active_market = Market.objects.create(
            premise="Active bidding market",
            unit_price=1.0,
            initial_spread=15,
            created_by=self.admin_user,
            spread_bidding_open=now - timedelta(hours=1),
            spread_bidding_close=now + timedelta(hours=1),  # Still active
            trading_open=now + timedelta(hours=2),
            trading_close=now + timedelta(hours=4)
        )
        
        result = active_market.auto_activate_market()
        
        self.assertFalse(result['success'])
        self.assertEqual(result['reason'], 'Market is not eligible for auto-activation')
        
        # Market should remain unchanged
        active_market.refresh_from_db()
        self.assertEqual(active_market.status, 'CREATED')
        self.assertIsNone(active_market.final_spread_low)

    def test_auto_activate_already_activated(self):
        """Test auto-activation when market is already activated"""
        # Activate the market first
        self.market.auto_activate_market()
        
        # Try to activate again
        result = self.market.auto_activate_market()
        
        self.assertFalse(result['success'])
        self.assertEqual(result['reason'], 'Market is not eligible for auto-activation')


class SpreadBidModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user1.profile.is_verified = True
        self.user1.profile.save()
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.user2.profile.is_verified = True
        self.user2.profile.save()
        
        now = timezone.now()
        self.market = Market.objects.create(
            premise="Test market for bidding",
            unit_price=1.0,
            initial_spread=20,
            created_by=self.user1,
            spread_bidding_open=now - timedelta(hours=1),
            spread_bidding_close=now + timedelta(hours=1),
            trading_open=now + timedelta(hours=2),
            trading_close=now + timedelta(hours=3)
        )

    def test_spread_bid_creation(self):
        """Test basic spread bid creation"""
        bid = SpreadBid.objects.create(
            market=self.market,
            user=self.user1,
            spread_low=40,
            spread_high=60
        )
        
        self.assertEqual(bid.spread_width, 20)
        self.assertEqual(bid.spread_display, "40 - 60")
        self.assertTrue(bid.bid_time)

    def test_spread_bid_validation(self):
        """Test spread bid validation"""
        from django.core.exceptions import ValidationError
        
        # Test invalid spread (low >= high)
        with self.assertRaises(ValidationError):
            bid = SpreadBid(
                market=self.market,
                user=self.user1,
                spread_low=60,
                spread_high=40
            )
            bid.clean()

    def test_multiple_bids_ordering(self):
        """Test that multiple bids are ordered correctly"""
        # Create bids with different spreads
        bid1 = SpreadBid.objects.create(
            market=self.market,
            user=self.user1,
            spread_low=40,
            spread_high=60  # width = 20
        )
        
        bid2 = SpreadBid.objects.create(
            market=self.market,
            user=self.user2,
            spread_low=45,
            spread_high=55  # width = 10 (better)
        )
        
        # Best bid should be the tighter one
        self.assertEqual(self.market.best_spread_bid, bid2)
        self.assertEqual(self.market.current_best_spread_width, 10)

    def test_user_best_bid(self):
        """Test getting user's best bid"""
        # User1 makes multiple bids
        bid1 = SpreadBid.objects.create(
            market=self.market,
            user=self.user1,
            spread_low=40,
            spread_high=60  # width = 20
        )
        
        bid2 = SpreadBid.objects.create(
            market=self.market,
            user=self.user1,
            spread_low=45,
            spread_high=55  # width = 10 (better)
        )
        
        # User's best bid should be the tighter one
        user_best = self.market.get_user_best_bid(self.user1)
        self.assertEqual(user_best, bid2)


class SpreadBidAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.profile.is_verified = True
        self.user.profile.save()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        now = timezone.now()
        self.market = Market.objects.create(
            premise="API Test Market",
            unit_price=1.0,
            initial_spread=15,
            created_by=self.admin_user,
            spread_bidding_open=now - timedelta(minutes=30),
            spread_bidding_close=now + timedelta(minutes=30),
            trading_open=now + timedelta(hours=1),
            trading_close=now + timedelta(hours=2)
        )

    def test_place_spread_bid_success(self):
        """Test successful spread bid placement"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'spread_low': 45,
            'spread_high': 55
        }
        
        response = self.client.post(
            f'/api/market/{self.market.id}/place_spread_bid/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['spread_low'], 45)
        self.assertEqual(response.data['spread_high'], 55)
        self.assertEqual(response.data['user_username'], 'testuser')

    def test_place_spread_bid_unverified_user(self):
        """Test that unverified users cannot place bids"""
        # Create unverified user
        unverified_user = User.objects.create_user(
            username='unverified',
            email='unverified@example.com',
            password='testpass123'
        )
        # Profile is created but not verified (is_verified defaults to False)
        
        self.client.force_authenticate(user=unverified_user)
        
        data = {
            'spread_low': 45,
            'spread_high': 55
        }
        
        response = self.client.post(
            f'/api/market/{self.market.id}/place_spread_bid/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('verified', str(response.data))

    def test_place_spread_bid_invalid_spread(self):
        """Test validation of spread values"""
        self.client.force_authenticate(user=self.user)
        
        # Invalid spread (low >= high)
        data = {
            'spread_low': 60,
            'spread_high': 40
        }
        
        response = self.client.post(
            f'/api/market/{self.market.id}/place_spread_bid/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_market_spread_bids(self):
        """Test retrieving spread bids for a market"""
        # Create some bids
        SpreadBid.objects.create(
            market=self.market,
            user=self.user,
            spread_low=45,
            spread_high=55
        )
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(f'/api/market/{self.market.id}/spread_bids/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user_username'], 'testuser')

    def test_market_serializer_includes_best_bid(self):
        """Test that market serializer includes best bid information"""
        # Create a bid
        SpreadBid.objects.create(
            market=self.market,
            user=self.user,
            spread_low=45,
            spread_high=55
        )
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get(f'/api/market/{self.market.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['best_spread_bid'])
        self.assertEqual(response.data['best_spread_bid']['user'], 'testuser')
        self.assertEqual(response.data['current_best_spread_width'], 10)

    def test_spread_bid_timing_validation(self):
        """Test that bids can only be placed during bidding window"""
        # Create a market with bidding window in the past
        past_market = Market.objects.create(
            premise="Past Market",
            unit_price=1.0,
            initial_spread=10,
            created_by=self.admin_user,
            spread_bidding_open=timezone.now() - timedelta(hours=2),
            spread_bidding_close=timezone.now() - timedelta(hours=1),
            trading_open=timezone.now() + timedelta(hours=1),
            trading_close=timezone.now() + timedelta(hours=2)
        )
        
        self.client.force_authenticate(user=self.user)
        
        data = {
            'spread_low': 45,
            'spread_high': 50
        }
        
        response = self.client.post(
            f'/api/market/{past_market.id}/place_spread_bid/',
            data
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('not currently active', str(response.data))


class MarketAutoActivationAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.profile.is_verified = True
        self.user.profile.save()
        
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='adminpass123',
            is_staff=True
        )
        
        # Create a market with closed bidding window
        now = timezone.now()
        self.market = Market.objects.create(
            premise="Auto-activation test market",
            unit_price=1.0,
            initial_spread=20,
            created_by=self.admin_user,
            spread_bidding_open=now - timedelta(hours=2),
            spread_bidding_close=now - timedelta(hours=1),  # Closed
            trading_open=now + timedelta(hours=1),
            trading_close=now + timedelta(hours=3)
        )

    def test_lazy_activation_on_market_list(self):
        """Test that markets are auto-activated when listing markets"""
        # Create a bid
        SpreadBid.objects.create(
            market=self.market,
            user=self.user,
            spread_low=45,
            spread_high=55
        )
        
        self.client.force_authenticate(user=self.user)
        
        # List markets - should trigger auto-activation
        response = self.client.get('/api/market/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that market was auto-activated
        self.market.refresh_from_db()
        self.assertEqual(self.market.status, 'OPEN')
        self.assertEqual(self.market.final_spread_low, 45)
        self.assertEqual(self.market.final_spread_high, 55)

    def test_lazy_activation_on_market_retrieve(self):
        """Test that market is auto-activated when retrieving specific market"""
        # Create a bid
        SpreadBid.objects.create(
            market=self.market,
            user=self.user,
            spread_low=40,
            spread_high=60
        )
        
        self.client.force_authenticate(user=self.user)
        
        # Retrieve specific market - should trigger auto-activation
        response = self.client.get(f'/api/market/{self.market.id}/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that market was auto-activated
        self.market.refresh_from_db()
        self.assertEqual(self.market.status, 'OPEN')
        self.assertEqual(response.data['status'], 'OPEN')
        self.assertEqual(response.data['final_spread_low'], 40)
        self.assertEqual(response.data['final_spread_high'], 60)

    def test_manual_activation_endpoint(self):
        """Test the manual activation endpoint for admins"""
        # Create a bid
        SpreadBid.objects.create(
            market=self.market,
            user=self.user,
            spread_low=42,
            spread_high=58
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        # Manually activate the market
        response = self.client.post(f'/api/market/{self.market.id}/manual_activate/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Market activated successfully')
        
        # Check market state
        self.market.refresh_from_db()
        self.assertEqual(self.market.status, 'OPEN')
        self.assertEqual(self.market.final_spread_low, 42)
        self.assertEqual(self.market.final_spread_high, 58)

    def test_manual_activation_non_admin(self):
        """Test that non-admin users cannot manually activate markets"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(f'/api/market/{self.market.id}/manual_activate/')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MarketViewSetTest(TestCase):
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
    
    def test_authenticated_user_can_view_market_detail(self):
        """Test that authenticated users can view market details"""
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
            'spread_bidding_open': (timezone.now() + timedelta(hours=1)).isoformat(),
            'spread_bidding_close': (timezone.now() + timedelta(hours=2)).isoformat(),
            'trading_open': (timezone.now() + timedelta(hours=3)).isoformat(),
            'trading_close': (timezone.now() + timedelta(hours=24)).isoformat()
        }
        
        response = self.client.post('/api/market/', market_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_admin_user_can_create_market(self):
        """Test that admin users can create markets"""
        self.client.force_authenticate(user=self.admin_user)
        
        base_time = timezone.now()
        market_data = {
            'premise': 'New market premise',
            'unit_price': 1.0,
            'initial_spread': 45,
            'spread_bidding_open': (base_time + timedelta(hours=1)).isoformat(),
            'spread_bidding_close': (base_time + timedelta(hours=2)).isoformat(),
            'trading_open': (base_time + timedelta(hours=3)).isoformat(),
            'trading_close': (base_time + timedelta(hours=24)).isoformat()
        }
        
        response = self.client.post('/api/market/', market_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['premise'], 'New market premise')
        self.assertEqual(response.data['created_by_username'], 'admin')
    
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
