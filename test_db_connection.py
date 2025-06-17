#!/usr/bin/env python3
"""
Test database connection for Mock Trading App
"""

import os
import sys
import django
from django.db import connection
from django.core.management import execute_from_command_line

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mock_trading.settings')

print("Testing Database Connection...")

try:
    # Initialize Django
    django.setup()
    
    # Test database connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        
    # Get database configuration
    from django.conf import settings
    db_config = settings.DATABASES['default']
    
    print(f"Database Engine: {db_config['ENGINE']}")
    print(f"Database Name: {db_config['NAME']}")
    print(f"Database Host: {db_config['HOST']}")
    print(f"Database Port: {db_config['PORT']}")
    print(f"SSL Options: {db_config.get('OPTIONS', {})}")
    
    if version:
        print(f"Connected to PostgreSQL: {version[0]}")
    
    print("Database connection successful!")
    
except Exception as e:
    print(f"Database connection failed: {e}")
    sys.exit(1)

# Test Django system check
try:
    print("\nRunning Django System Check...")
    from django.core.management import call_command
    from io import StringIO
    
    call_command('check', verbosity=0)
    print("Django system check passed!")
    
except Exception as e:
    print(f"Django system check failed: {e}")

# Test basic model operations
try:
    from django.contrib.auth.models import User
    from market.models import Market
    
    # Count existing records
    user_count = User.objects.count()
    market_count = Market.objects.count()
    
    print(f"\nDatabase Statistics:")
    print(f"Users: {user_count}")
    print(f"Markets: {market_count}")
    
except Exception as e:
    print(f"Model operations failed: {e}")

print("\nTest completed!") 