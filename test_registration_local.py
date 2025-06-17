#!/usr/bin/env python3
"""
Simple script to test the registration endpoint locally
"""
import requests
import json
import sys
import os

def test_registration():
    """Test the registration endpoint"""
    # Use environment variable or default to localhost for testing
    base_url = os.environ.get('API_BASE_URL', 'http://localhost:8000')
    url = f'{base_url}/api/auth/register/'
    
    # Test data
    test_data = {
        'username': 'newuser123',
        'password': 'securepassword123',
        'password2': 'securepassword123',
        'email': 'newuser@example.com',
        'first_name': 'New',
        'last_name': 'User'
    }
    
    try:
        print("Testing registration endpoint...")
        print(f"URL: {url}")
        print(f"Data: {json.dumps(test_data, indent=2)}")
        print("-" * 50)
        
        response = requests.post(url, json=test_data, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("Registration successful!")
            print(f"Response: {response.json()}")
            return True
        else:
            print("Registration failed")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to server.")
        print("Make sure Django server is running: python manage.py runserver")
        print("For local testing: python manage.py runserver")
        print("For Azure testing: set API_BASE_URL=https://salonis-mock-trading-app.azurewebsites.net")
        return False
    except requests.exceptions.Timeout:
        print("Request timed out")
        print("Server might be slow to respond")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    success = test_registration()
    sys.exit(0 if success else 1) 