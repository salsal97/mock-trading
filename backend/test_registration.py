#!/usr/bin/env python
import os
import sys
import django
import requests
import json

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mock_trading.settings')
django.setup()

def test_registration():
    """Test the registration endpoint"""
    url = 'http://localhost:8000/api/auth/register/'
    
    # Test data
    test_data = {
        'username': 'testuser123',
        'password': 'testpassword123',
        'password2': 'testpassword123',
        'email': 'test@example.com',
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    try:
        response = requests.post(url, json=test_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 201:
            print("✅ Registration successful!")
        else:
            print("❌ Registration failed")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_duplicate_registration():
    """Test registration with duplicate username"""
    url = 'http://localhost:8000/api/auth/register/'
    
    # Test data with duplicate username
    test_data = {
        'username': 'testuser123',  # Same as above
        'password': 'testpassword456',
        'password2': 'testpassword456',
        'email': 'test2@example.com',
        'first_name': 'Test2',
        'last_name': 'User2'
    }
    
    try:
        response = requests.post(url, json=test_data)
        print(f"\nDuplicate Username Test:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✅ Duplicate username properly rejected!")
        else:
            print("❌ Duplicate username test failed")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    print("Testing Registration Endpoint...")
    test_registration()
    test_duplicate_registration() 