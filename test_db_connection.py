#!/usr/bin/env python3
"""
Test database connection for both local and CI environments
"""
import os
import sys
import django

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mock_trading.settings')

def test_database_connection():
    """Test database connection"""
    print("🔧 Testing Database Connection...")
    
    try:
        django.setup()
        from django.db import connection
        from django.conf import settings
        
        # Print database configuration
        db_config = settings.DATABASES['default']
        print(f"📊 Database Engine: {db_config['ENGINE']}")
        print(f"📊 Database Name: {db_config['NAME']}")
        print(f"📊 Database Host: {db_config['HOST']}")
        print(f"📊 Database Port: {db_config['PORT']}")
        print(f"📊 SSL Options: {db_config.get('OPTIONS', {})}")
        
        # Test connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Connected to PostgreSQL: {version[0]}")
            
        print("✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_django_check():
    """Test Django system check"""
    print("\n🔍 Running Django System Check...")
    
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'check'])
        print("✅ Django system check passed!")
        return True
    except Exception as e:
        print(f"❌ Django system check failed: {e}")
        return False

if __name__ == '__main__':
    print("🧪 Database Connection Test")
    print("=" * 40)
    
    # Set minimal required environment variables for testing
    if not os.environ.get('SECRET_KEY'):
        os.environ['SECRET_KEY'] = 'test-secret-key-for-connection-test'
    
    success = test_database_connection()
    if success:
        test_django_check()
    
    print("\n🎉 Test completed!") 