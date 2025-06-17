#!/usr/bin/env python3
"""
Test script for Trading API functionality
Tests the new trade endpoints and functionality
"""

import requests
import json
from datetime import datetime, timedelta
import os

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'https://salonis-mock-trading-app.azurewebsites.net')
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

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
        'spread_bidding_close': (now - timedelta(hours=1)).isoformat(),
        'trading_open': (now - timedelta(minutes=30)).isoformat(),
        'trading_close': (now + timedelta(hours=2)).isoformat()
    }
    
    response = requests.post(f'{API_BASE_URL}/api/market/', 
                           json=market_data, headers=headers)
    
    if response.status_code == 201:
        market = response.json()
        print(f"Created test market: {market['id']}")
        
        # Auto-activate the market (since no spread bids)
        activate_response = requests.post(
            f'{API_BASE_URL}/api/market/{market["id"]}/auto_activate/',
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

def test_trade_validation():
    """Test trade validation rules"""
    print("\n=== Testing Trade Validation ===")
    
    # This would require creating a regular user account
    # For now, we'll just test with admin (which should fail for market maker rule)
    print("Trade validation tests would require regular user accounts")
    print("Admin users cannot trade on markets (market maker restriction)")

def main():
    print("Testing Trading API Functionality")
    print("=" * 50)
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("Failed to authenticate admin user")
        return
    
    print("Admin authentication successful")
    
    # Create test market
    market_id = create_test_market(token)
    if not market_id:
        print("Failed to create test market")
        return
    
    # Test trading endpoints
    success = test_trading_endpoints(token, market_id)
    
    if success:
        print("\n" + "=" * 50)
        print("Trading API tests completed!")
        print("Check the admin dashboard to see trade statistics")
    else:
        print("\nSome tests failed - check the output above")

if __name__ == '__main__':
    main() 