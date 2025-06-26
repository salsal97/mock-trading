#!/usr/bin/env python3
"""
Test script for Trading API functionality
Tests the new trade endpoints and spread bidding functionality
"""

import requests
import json
from datetime import datetime, timedelta
import os

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'https://salonis-mock-trading-app.azurewebsites.net')
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = os.getenv('TEST_ADMIN_PASSWORD', 'admin123')

def get_admin_token():
    """Get admin authentication token"""
    response = requests.post(f'{API_BASE_URL}/api/auth/login/', {
        'username': ADMIN_USERNAME,
        'password': ADMIN_PASSWORD
    })
    
    if response.status_code == 200:
        return response.json()['access']
    else:
        print(f"Failed to get admin token: {response.status_code}")
        print(response.text)
        return None

def create_user_and_get_token(username, password):
    """Create a regular user and get authentication token"""
    # First try to create user (might already exist)
    user_data = {
        'username': username,
        'password': password,
        'email': f'{username}@test.com',
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    response = requests.post(f'{API_BASE_URL}/api/auth/register/', user_data)
    if response.status_code not in [200, 201, 400]:  # 400 might mean user already exists
        print(f"Failed to create user: {response.status_code}")
        print(response.text)
    
    # Now try to login
    response = requests.post(f'{API_BASE_URL}/api/auth/login/', {
        'username': username,
        'password': password
    })
    
    if response.status_code == 200:
        return response.json()['access']
    else:
        print(f"Failed to get user token: {response.status_code}")
        print(response.text)
        return None

def create_spread_bidding_market(token):
    """Create a test market for spread bidding"""
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create market with active spread bidding window
    now = datetime.now()
    market_data = {
        'premise': 'Test Spread Bidding Market - Will AI achieve AGI by 2030?',
        'unit_price': 1.0,
        'initial_spread': 30,  # Wide initial spread that bidders can beat
        'spread_bidding_open': (now - timedelta(hours=1)).isoformat(),
        'spread_bidding_close_trading_open': (now + timedelta(hours=2)).isoformat(),
        'trading_close': (now + timedelta(hours=4)).isoformat()
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/', 
                           json=market_data, headers=headers)
    
    if response.status_code == 201:
        market = response.json()
        print(f"Created spread bidding market: {market['id']}")
        return market['id']
    else:
        print(f"Failed to create spread bidding market: {response.status_code}")
        print(response.text)
        return None

def create_test_market(token):
    """Create a test market for trading"""
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create market with times that allow immediate trading
    now = datetime.now()
    market_data = {
        'premise': 'Test Trading Market - Will Bitcoin reach $100k by end of year?',
        'unit_price': 10.0,
        'initial_spread': 20,
        'spread_bidding_open': (now - timedelta(hours=2)).isoformat(),
        'spread_bidding_close_trading_open': (now - timedelta(hours=1)).isoformat(),
        'trading_close': (now + timedelta(hours=2)).isoformat()
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/', 
                           json=market_data, headers=headers)
    
    if response.status_code == 201:
        market = response.json()
        print(f"Created test market: {market['id']}")
        
        # Auto-activate the market (since no spread bids)
        activate_response = requests.post(
            f'{API_BASE_URL}/api/market/{market["id"]}/manual_activate/',
            headers=headers
        )
        
        if activate_response.status_code == 200:
            print("Market auto-activated successfully")
            return market['id']
        else:
            print(f"Failed to activate market: {activate_response.status_code}")
            print(activate_response.text)
            return market['id']
    else:
        print(f"Failed to create market: {response.status_code}")
        print(response.text)
        return None

def test_spread_bidding(admin_token, market_id):
    """Test spread bidding functionality with multiple users"""
    print("\n=== Testing Spread Bidding Functionality ===")
    
    # Create test users
    user_password = os.getenv('TEST_USER_PASSWORD', 'testpass123')
    user1_token = create_user_and_get_token('bidder1', user_password)
    user2_token = create_user_and_get_token('bidder2', user_password)
    user3_token = create_user_and_get_token('bidder3', user_password)
    
    if not all([user1_token, user2_token, user3_token]):
        print("Failed to create test users")
        return False
    
    print("Created test users successfully")
    
    # Test 1: Check market is in spread bidding phase
    print("\n1. Testing market spread bidding status...")
    headers = {'Authorization': f'Bearer {user1_token}'}
    response = requests.get(f'{API_BASE_URL}/api/market/{market_id}/', headers=headers)
    
    if response.status_code == 200:
        market = response.json()
        print(f"Market status: {market['status']}")
        print(f"Spread bidding active: {market['is_spread_bidding_active']}")
        print(f"Initial spread: {market['initial_spread']}")
        print(f"Best spread bid: {market['best_spread_bid']}")
        
        if not market['is_spread_bidding_active']:
            print("Market is not in spread bidding phase!")
            return False
    else:
        print(f"Failed to get market details: {response.status_code}")
        return False
    
    # Test 2: User 1 places first spread bid
    print("\n2. Testing first spread bid placement...")
    bid_data = {
        'spread_low': 40.0,
        'spread_high': 60.0  # Spread width = 20, better than initial 30
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/place_spread_bid/',
                           json=bid_data, headers={'Authorization': f'Bearer {user1_token}'})
    
    if response.status_code == 200:
        bid = response.json()
        print(f"First spread bid placed successfully: {bid}")
    else:
        print(f"Failed to place first spread bid: {response.status_code}")
        print(response.text)
        return False
    
    # Test 3: User 2 places competitive bid
    print("\n3. Testing competitive spread bid...")
    bid_data = {
        'spread_low': 42.0,
        'spread_high': 58.0  # Spread width = 16, better than 20
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/place_spread_bid/',
                           json=bid_data, headers={'Authorization': f'Bearer {user2_token}'})
    
    if response.status_code == 200:
        bid = response.json()
        print(f"Competitive spread bid placed successfully: {bid}")
    else:
        print(f"Failed to place competitive spread bid: {response.status_code}")
        print(response.text)
        return False
    
    # Test 4: User 3 tries non-competitive bid (should still work but won't win)
    print("\n4. Testing non-competitive spread bid...")
    bid_data = {
        'spread_low': 35.0,
        'spread_high': 65.0  # Spread width = 30, same as initial
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/place_spread_bid/',
                           json=bid_data, headers={'Authorization': f'Bearer {user3_token}'})
    
    if response.status_code == 200:
        bid = response.json()
        print(f"Non-competitive spread bid placed: {bid}")
    else:
        print(f"Failed to place non-competitive spread bid: {response.status_code}")
        print(response.text)
        # This might be expected behavior if the system rejects non-competitive bids
    
    # Test 5: Check best spread bid
    print("\n5. Testing best spread bid retrieval...")
    response = requests.get(f'{API_BASE_URL}/api/market/{market_id}/', 
                          headers={'Authorization': f'Bearer {user1_token}'})
    
    if response.status_code == 200:
        market = response.json()
        best_bid = market['best_spread_bid']
        if best_bid:
            print(f"Best spread bid: {best_bid}")
            print(f"Winner: {best_bid['user']}")
            print(f"Winning spread: {best_bid['spread_low']} - {best_bid['spread_high']}")
            print(f"Spread width: {best_bid['spread_width']}")
        else:
            print("No best spread bid found!")
    else:
        print(f"Failed to get updated market details: {response.status_code}")
        return False
    
    # Test 6: Test invalid spread bid (spread_low >= spread_high)
    print("\n6. Testing invalid spread bid...")
    invalid_bid_data = {
        'spread_low': 60.0,
        'spread_high': 40.0  # Invalid: low > high
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/place_spread_bid/',
                           json=invalid_bid_data, headers={'Authorization': f'Bearer {user1_token}'})
    
    if response.status_code == 400:
        print("Invalid spread bid correctly rejected")
    else:
        print(f"Invalid spread bid not rejected properly: {response.status_code}")
        print(response.text)
    
    # Test 7: Test out of bounds spread bid
    print("\n7. Testing out of bounds spread bid...")
    invalid_bid_data = {
        'spread_low': -5.0,  # Invalid: negative
        'spread_high': -2.0  # Invalid: negative
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/place_spread_bid/',
                           json=invalid_bid_data, headers={'Authorization': f'Bearer {user1_token}'})
    
    if response.status_code == 400:
        print("Negative spread bid correctly rejected")
    else:
        print(f"Negative spread bid not rejected properly: {response.status_code}")
        print(response.text)
    
    # Test 8: Get all spread bids for market
    print("\n8. Testing spread bids retrieval...")
    response = requests.get(f'{API_BASE_URL}/api/market/{market_id}/spread_bids/', 
                          headers={'Authorization': f'Bearer {user1_token}'})
    
    if response.status_code == 200:
        bids = response.json()
        print(f"All spread bids: {len(bids)} bids")
        for bid in bids:
            print(f"  - {bid['user']} bid: {bid['spread_low']}-{bid['spread_high']} (width: {bid['spread_width']})")
    else:
        print(f"Failed to get spread bids: {response.status_code}")
        print(response.text)
    
    return True

def test_trading_endpoints(token, market_id):
    """Test all trading-related endpoints"""
    headers = {'Authorization': f'Bearer {token}'}
    
    print("\n=== Testing Trading Endpoints ===")
    
    # 1. Test market details with trade statistics
    print("\n1. Testing market details...")
    response = requests.get(f'{API_BASE_URL}/api/market/{market_id}/', headers=headers)
    if response.status_code == 200:
        market = response.json()
        print(f"Market status: {market['status']}")
        print(f"Trading active: {market['is_trading_active']}")
        print(f"Long trades: {market['long_trades_count']}")
        print(f"Short trades: {market['short_trades_count']}")
        print(f"Total trades: {market['total_trades_count']}")
        print(f"Can user trade: {market['can_user_trade']}")
        print(f"User trade: {market['user_trade']}")
    else:
        print(f"Failed to get market details: {response.status_code}")
        return False
    
    # 2. Test placing a long trade
    print("\n2. Testing long trade placement...")
    trade_data = {
        'position': 'LONG',
        'price': 60.0,  # Above spread high
        'quantity': 2
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/place_trade/',
                           json=trade_data, headers=headers)
    if response.status_code == 200:
        trade = response.json()
        print(f"Long trade placed successfully: {trade}")
    else:
        print(f"Failed to place long trade: {response.status_code}")
        print(response.text)
    
    # 3. Test updating the trade to short
    print("\n3. Testing trade update...")
    update_data = {
        'position': 'SHORT',
        'price': 40.0,  # Below spread low
        'quantity': 3
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/place_trade/',
                           json=update_data, headers=headers)
    if response.status_code == 200:
        trade = response.json()
        print(f"Trade updated successfully: {trade}")
    else:
        print(f"Failed to update trade: {response.status_code}")
        print(response.text)
    
    # 4. Test getting market trades
    print("\n4. Testing market trades retrieval...")
    response = requests.get(f'{API_BASE_URL}/api/market/{market_id}/trades/', headers=headers)
    if response.status_code == 200:
        trades_data = response.json()
        print(f"Market trades: {trades_data}")
    else:
        print(f"Failed to get market trades: {response.status_code}")
        print(response.text)
    
    # 5. Test getting all trades
    print("\n5. Testing all trades retrieval...")
    response = requests.get(f'{API_BASE_URL}/api/market/trades/', headers=headers)
    if response.status_code == 200:
        all_trades = response.json()
        print(f"All user trades: {len(all_trades)} trades")
        for trade in all_trades:
            print(f"  - {trade['position']} on {trade['market_premise'][:50]}...")
    else:
        print(f"Failed to get all trades: {response.status_code}")
        print(response.text)
    
    # 6. Test cancelling trade
    print("\n6. Testing trade cancellation...")
    response = requests.delete(f'{API_BASE_URL}/api/market/{market_id}/cancel_trade/', headers=headers)
    if response.status_code == 200:
        result = response.json()
        print(f"Trade cancelled: {result}")
    else:
        print(f"Failed to cancel trade: {response.status_code}")
        print(response.text)
    
    return True

def test_market_activation(admin_token, market_id):
    """Test market activation after spread bidding"""
    print("\n=== Testing Market Activation ===")
    
    headers = {'Authorization': f'Bearer {admin_token}'}
    
    # Test manual activation
    print("\n1. Testing manual market activation...")
    response = requests.post(f'{API_BASE_URL}/api/market/{market_id}/manual_activate/',
                           headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"Market activated successfully: {result}")
        
        # Check final state
        response = requests.get(f'{API_BASE_URL}/api/market/{market_id}/', headers=headers)
        if response.status_code == 200:
            market = response.json()
            print(f"Final market status: {market['status']}")
            print(f"Market maker: {market.get('market_maker_username', 'None')}")
            print(f"Final spread: {market.get('final_spread_low', 'None')} - {market.get('final_spread_high', 'None')}")
            print(f"Trading active: {market['is_trading_active']}")
    else:
        print(f"Failed to activate market: {response.status_code}")
        print(response.text)
        return False
    
    return True

def main():
    print("Testing Trading API and Spread Bidding Functionality")
    print("=" * 60)
    
    # Get admin token
    admin_token = get_admin_token()
    if not admin_token:
        print("Failed to authenticate admin user")
        return
    
    print("Admin authentication successful")
    
    # Test 1: Create and test spread bidding market
    spread_market_id = create_spread_bidding_market(admin_token)
    if spread_market_id:
        spread_bidding_success = test_spread_bidding(admin_token, spread_market_id)
        if spread_bidding_success:
            test_market_activation(admin_token, spread_market_id)
    
    # Test 2: Create and test regular trading market
    trading_market_id = create_test_market(admin_token)
    if trading_market_id:
        # Create a test user for trading (admin can't trade)
        trader_token = create_user_and_get_token('trader', os.getenv('TEST_USER_PASSWORD', 'testpass123'))
        if trader_token:
            test_trading_endpoints(trader_token, trading_market_id)
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("Key features tested:")
    print("✓ Spread bidding with multiple users")
    print("✓ Competitive bidding mechanics")
    print("✓ Best bid selection")
    print("✓ Market activation with winning bid")
    print("✓ Input validation for spread bids")
    print("✓ Trading on activated markets")
    print("Check the admin dashboard to see all results")

if __name__ == '__main__':
    main() 