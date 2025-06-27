from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from market.models import Market, SpreadBid, Trade
from accounts.models import UserProfile
import uuid


class MarketTestCase(TestCase):
    """Comprehensive test suite for market functionality including no-bids delay rule."""
    
    def setUp(self):
        """Set up test data using unique usernames to avoid conflicts."""
        # Create unique usernames to prevent conflicts
        unique_id = uuid.uuid4().hex[:8]
        
        self.creator = User.objects.create_user(
            username=f'creator_{unique_id}',
            email=f'creator_{unique_id}@test.com',
            password='testpass123'
        )
        self.bidder = User.objects.create_user(
            username=f'bidder_{unique_id}', 
            email=f'bidder_{unique_id}@test.com',
            password='testpass123'
        )
        self.trader = User.objects.create_user(
            username=f'trader_{unique_id}',
            email=f'trader_{unique_id}@test.com', 
            password='testpass123'
        )
        
        # Ensure all users have verified profiles  
        # (User creation triggers profile creation via signals, but they need to be verified)
        for user in [self.creator, self.bidder, self.trader]:
            profile = user.profile
            profile.balance = Decimal('1000.00')
            profile.is_verified = True
            profile.save()
        
        self.now = timezone.now()

    def create_market(self, bidding_close_offset_hours=1, trading_close_offset_hours=3):
        """Helper to create a test market."""
        return Market.objects.create(
            premise=f"Test market {uuid.uuid4().hex[:8]}",
            unit_price=100.0,
            initial_spread=20,
            spread_bidding_open=self.now - timedelta(hours=2),
            spread_bidding_close_trading_open=self.now + timedelta(hours=bidding_close_offset_hours),
            trading_close=self.now + timedelta(hours=trading_close_offset_hours),
            created_by=self.creator
        )

    def create_bid(self, market, user=None, spread_low=45, spread_high=55):
        """Helper to create a spread bid."""
        return SpreadBid.objects.create(
            market=market,
            user=user or self.bidder,
            spread_low=spread_low,
            spread_high=spread_high
        )


    # === NO-BIDS DELAY FUNCTIONALITY TESTS ===
    
    def test_no_bids_delay_property_logic(self):
        """Test should_delay_for_no_bids property identifies correct markets."""
        # Market with closed bidding, no bids = should delay
        market = self.create_market(bidding_close_offset_hours=-1)
        self.assertTrue(market.should_delay_for_no_bids)
        self.assertEqual(market.spread_bids.count(), 0)
        
        # Create market with active bidding to test with bids
        market_with_active_bidding = self.create_market(bidding_close_offset_hours=1)  # Still open
        self.create_bid(market_with_active_bidding)
        
        # Manually close bidding and check delay logic
        market_with_active_bidding.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market_with_active_bidding.save()
        market_with_active_bidding.refresh_from_db()
        self.assertFalse(market_with_active_bidding.should_delay_for_no_bids)  # Has bids, so no delay

    def test_delay_market_execution_success(self):
        """Test successful market delay extends times by 24 hours."""
        market = self.create_market(bidding_close_offset_hours=-1, trading_close_offset_hours=1)
        original_bidding = market.spread_bidding_close_trading_open
        original_trading = market.trading_close
        
        result = market.delay_market_for_no_bids()
        
        # Verify success and times extended
        self.assertTrue(result['success'])
        self.assertIn('delayed by 1 day', result['reason'])
        market.refresh_from_db()
        self.assertEqual(market.spread_bidding_close_trading_open, original_bidding + timedelta(days=1))
        self.assertEqual(market.trading_close, original_trading + timedelta(days=1))

    def test_delay_fails_with_existing_bids(self):
        """Test delay fails when market has bids."""
        # Create market with active bidding, add bid, then close bidding
        market = self.create_market(bidding_close_offset_hours=1)  # Still open
        self.create_bid(market)
        
        # Close bidding manually
        market.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market.save()
        
        result = market.delay_market_for_no_bids()
        self.assertFalse(result['success'])

    def test_multiple_delays_accumulate(self):
        """Test market can be delayed multiple times by simulating time passage."""
        market = self.create_market(bidding_close_offset_hours=-1)
        original_time = market.spread_bidding_close_trading_open
        
        # First delay
        result1 = market.delay_market_for_no_bids()
        self.assertTrue(result1['success'], f"First delay failed: {result1}")
        market.refresh_from_db()
        
        # Verify first delay worked
        self.assertEqual(market.spread_bidding_close_trading_open, original_time + timedelta(days=1))
        
        # Simulate passage of time - make the new bidding close time also passed
        # by manually setting it to past time to test another delay
        market.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market.save()
        
        # Now market should be eligible for another delay
        self.assertTrue(market.should_delay_for_no_bids, "Market should be eligible for second delay")
        
        # Second delay
        result2 = market.delay_market_for_no_bids()
        self.assertTrue(result2['success'], f"Second delay failed: {result2}")
        market.refresh_from_db()
        
        # Verify second delay added another day
        expected_final_time = self.now - timedelta(hours=1) + timedelta(days=1)  # From where we set it
        self.assertEqual(market.spread_bidding_close_trading_open, expected_final_time)

    def test_current_spread_display_shows_delay_status(self):
        """Test UI display shows delay message when appropriate."""
        market = self.create_market(bidding_close_offset_hours=-1)
        self.assertEqual(market.current_spread_display, "No bids - will delay by 1 day")
        
        # Test with market that has bids
        market_with_bids = self.create_market(bidding_close_offset_hours=1)  # Active bidding
        self.create_bid(market_with_bids, spread_low=45, spread_high=55)
        self.assertEqual(market_with_bids.current_spread_display, "Best: 10")

    # === MARKET ACTIVATION INTEGRATION TESTS ===
    
    def test_activation_vs_delay_logic(self):
        """Test markets activate with bids, delay without bids."""
        market_no_bids = self.create_market(bidding_close_offset_hours=-1)
        
        # Create market with bids during active period, then close
        market_with_bids = self.create_market(bidding_close_offset_hours=1)
        self.create_bid(market_with_bids)
        market_with_bids.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market_with_bids.save()
        
        # No bids = delay, not activate
        self.assertTrue(market_no_bids.should_delay_for_no_bids)
        self.assertFalse(market_no_bids.should_auto_activate)
        
        # With bids = activate, not delay
        self.assertTrue(market_with_bids.should_auto_activate)
        self.assertFalse(market_with_bids.should_delay_for_no_bids)

    def test_market_activation_with_multiple_bids(self):
        """Test activation selects tightest bid."""
        # Create market with active bidding
        market = self.create_market(bidding_close_offset_hours=1)
        
        # Create bids with different spreads during active period
        self.create_bid(market, self.bidder, spread_low=40, spread_high=60)   # width: 20
        self.create_bid(market, self.trader, spread_low=45, spread_high=55)   # width: 10 (tighter)
        
        # Close bidding manually to trigger activation
        market.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market.save()
        
        result = market.auto_activate_market()
        
        self.assertTrue(result['success'])
        market.refresh_from_db()
        self.assertEqual(market.status, 'OPEN')
        self.assertEqual(market.final_spread_low, 45)  # Tighter bid won
        self.assertEqual(market.market_maker, self.trader)

    # === SETTLEMENT FUNCTIONALITY TESTS ===
    
    def test_settlement_price_setting(self):
        """Test settlement price can be set on closed markets."""
        market = self.create_market(bidding_close_offset_hours=1)
        self.create_bid(market)
        
        # Close bidding and activate
        market.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market.save()
        market.auto_activate_market()
        market.status = 'CLOSED'
        market.save()
        
        price = Decimal('150.00')
        result = market.set_settlement_price(price)
        
        self.assertEqual(result, price)
        market.refresh_from_db()
        self.assertEqual(market.settlement_price, price)

    def test_settlement_calculation_with_trades(self):
        """Test P&L calculation for settlement preview."""
        market = self.create_market(bidding_close_offset_hours=1)
        self.create_bid(market)
        
        # Close bidding and activate
        market.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market.save()
        market.auto_activate_market()
        
        # Create trade while market is OPEN (use correct market price)
        Trade.objects.create(market=market, user=self.trader, position='LONG', price=market.final_spread_high)
        
        # Now close market and settle
        market.status = 'CLOSED'
        market.save()
        
        market.set_settlement_price(Decimal('150.00'))
        preview = market.calculate_settlement_preview()
        
        self.assertEqual(len(preview['trades']), 1)
        # Calculate expected P&L: settlement price - market high price
        expected_pnl = Decimal('150.00') - market.final_spread_high
        self.assertEqual(preview['trades'][0]['profit_loss'], expected_pnl)
        self.assertEqual(preview['market_maker_impact'], -expected_pnl)  # Opposite of trader

    # === TRADING ELIGIBILITY TESTS ===
    
    def test_trading_eligibility_rules(self):
        """Test who can and cannot trade on markets."""
        market = self.create_market(bidding_close_offset_hours=1)
        self.create_bid(market)
        
        # Close bidding and activate (keep market OPEN for trading)
        market.spread_bidding_close_trading_open = self.now - timedelta(hours=1)
        market.save()
        market.auto_activate_market()
        
        # Verify market is OPEN
        market.refresh_from_db()
        self.assertEqual(market.status, 'OPEN')
        
        # Regular user can trade (neither creator nor market maker)
        can_trade, msg = market.can_user_trade(self.trader)
        self.assertTrue(can_trade, f"Trader should be able to trade but got: {msg}")
        
        # Market maker (bidder who won) cannot trade
        can_trade, msg = market.can_user_trade(self.bidder)  # bidder is the market maker
        self.assertFalse(can_trade, f"Market maker should not be able to trade. Got: {msg}")
        self.assertIn('Market makers cannot trade', msg)
        
        # Original market creator can still trade (since created_by was updated to winner)
        can_trade, msg = market.can_user_trade(self.creator)  
        self.assertTrue(can_trade, f"Original creator should be able to trade since they're no longer the creator. Got: {msg}") 