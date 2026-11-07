from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import UserProfile
from decimal import Decimal
import uuid


class UserProfileTestCase(TestCase):
    """Test user profile functionality and business rules"""
    
    def setUp(self):
        """Set up test data"""
        self.test_id = str(uuid.uuid4())[:8]
        self.client = APIClient()
        # Remove user and admin creation from setUp

    def test_user_profile_creation(self):
        """Test that user profiles are created correctly"""
        user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4()}',
            email=f'testuser_{uuid.uuid4()}@example.com',
            password='testpass123'
        )
        # Profile is automatically created by signals, so just get it
        profile = user.profile
        
        self.assertEqual(profile.user, user)
        self.assertEqual(profile.balance, Decimal('1000.00'))  # Default from model

    def test_user_profile_balance_validation(self):
        """Test that balance validation works correctly"""
        user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4()}',
            email=f'testuser_{uuid.uuid4()}@example.com',
            password='testpass123'
        )
        # Test negative balance (should be allowed for debt tracking)
        profile = user.profile  # Get automatically created profile
        profile.balance = -500.00
        profile.save()
        self.assertEqual(profile.balance, Decimal('-500.00'))
        
        # Test zero balance
        profile.balance = 0.00
        profile.save()
        self.assertEqual(profile.balance, Decimal('0.00'))

    def test_user_string_representation(self):
        """Test string representation of user profile"""
        user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4()}',
            email=f'testuser_{uuid.uuid4()}@example.com',
            password='testpass123'
        )
        profile = user.profile  # Get automatically created profile
        
        expected = f"{user.username} - Balance: $1000.00"
        self.assertEqual(str(profile), expected)

    def test_user_profile_uniqueness(self):
        """Test that each user can only have one profile"""
        user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4()}',
            email=f'testuser_{uuid.uuid4()}@example.com',
            password='testpass123'
        )
        # Profile is automatically created by signals
        profile1 = user.profile
        
        # Verify only one profile exists initially
        initial_count = UserProfile.objects.filter(user=user).count()
        self.assertEqual(initial_count, 1)
        
        # Attempting to create second profile should raise IntegrityError due to unique constraint
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            UserProfile.objects.create(
                user=user,
                balance=2000.00
            )

    def test_regular_user_properties(self):
        """Test that regular users have correct default properties"""
        user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4()}',
            email=f'testuser_{uuid.uuid4()}@example.com',
            password='testpass123'
        )
        profile = user.profile  # Get automatically created profile
        
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_balance_decimal_precision(self):
        """Test that balance maintains proper decimal precision"""
        user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4()}',
            email=f'testuser_{uuid.uuid4()}@example.com',
            password='testpass123'
        )
        profile = user.profile  # Get automatically created profile
        profile.balance = 1234.56789  # More precision than expected
        profile.save()
        
        # Should maintain 2 decimal places for currency
        profile.refresh_from_db()
        self.assertEqual(profile.balance, Decimal('1234.57'))  # Rounded to 2 places

    def test_user_profile_cascade_deletion(self):
        """Test that profile is handled correctly when user is deleted"""
        user = User.objects.create_user(
            username=f'testuser_{uuid.uuid4()}',
            email=f'testuser_{uuid.uuid4()}@example.com',
            password='testpass123'
        )
        profile = user.profile  # Get automatically created profile
        
        profile_id = profile.id
        user_id = user.id
        
        # Delete user
        user.delete()
        
        # Profile should also be deleted (CASCADE)
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)
        
        # User should be deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)
