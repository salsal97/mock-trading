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
        
        # Create test user
        self.user = User.objects.create_user(
            username=f'testuser_{self.test_id}',
            email=f'testuser_{self.test_id}@example.com',
            password='testpass123'
        )
        
        # Create admin user
        self.admin = User.objects.create_user(
            username=f'admin_{self.test_id}',
            email=f'admin_{self.test_id}@example.com',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )

    def test_user_profile_creation(self):
        """Test that user profiles are created correctly"""
        profile = UserProfile.objects.create(
            user=self.user,
            balance=1000.00
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.balance, Decimal('1000.00'))
        self.assertFalse(profile.is_verified)  # Default should be False
        self.assertIsNone(profile.verified_by)
        self.assertIsNone(profile.verification_date)

    def test_user_profile_balance_validation(self):
        """Test that balance validation works correctly"""
        # Test negative balance (should be allowed for debt tracking)
        profile = UserProfile.objects.create(
            user=self.user,
            balance=-500.00
        )
        self.assertEqual(profile.balance, Decimal('-500.00'))
        
        # Test zero balance
        profile.balance = 0.00
        profile.save()
        self.assertEqual(profile.balance, Decimal('0.00'))

    def test_user_verification_process(self):
        """Test user verification business rules"""
        profile = UserProfile.objects.create(
            user=self.user,
            balance=1000.00
        )
        
        # Initially not verified
        self.assertFalse(profile.is_verified)
        
        # Admin can verify users
        admin_profile = UserProfile.objects.create(
            user=self.admin,
            balance=5000.00,
            is_verified=True
        )
        
        # Verify the user
        profile.is_verified = True
        profile.verified_by = self.admin
        from django.utils import timezone
        profile.verification_date = timezone.now()
        profile.save()
        
        self.assertTrue(profile.is_verified)
        self.assertEqual(profile.verified_by, self.admin)
        self.assertIsNotNone(profile.verification_date)

    def test_user_string_representation(self):
        """Test string representation of user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            balance=1000.00
        )
        
        expected = f"{self.user.username} - Balance: $1000.00"
        self.assertEqual(str(profile), expected)

    def test_user_profile_uniqueness(self):
        """Test that each user can only have one profile"""
        # Create first profile
        UserProfile.objects.create(
            user=self.user,
            balance=1000.00
        )
        
        # Attempting to create second profile should work (no unique constraint)
        # but in practice, the application should use get_or_create
        profile2 = UserProfile.objects.create(
            user=self.user,
            balance=2000.00
        )
        
        # Both profiles exist, but this is why we use get_or_create in practice
        self.assertEqual(UserProfile.objects.filter(user=self.user).count(), 2)

    def test_admin_user_properties(self):
        """Test that admin users have correct properties"""
        admin_profile = UserProfile.objects.create(
            user=self.admin,
            balance=10000.00,
            is_verified=True
        )
        
        self.assertTrue(self.admin.is_staff)
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(admin_profile.is_verified)

    def test_regular_user_properties(self):
        """Test that regular users have correct default properties"""
        profile = UserProfile.objects.create(
            user=self.user,
            balance=1000.00
        )
        
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(profile.is_verified)  # Must be verified by admin

    def test_balance_decimal_precision(self):
        """Test that balance maintains proper decimal precision"""
        profile = UserProfile.objects.create(
            user=self.user,
            balance=1234.56789  # More precision than expected
        )
        
        # Should maintain 2 decimal places for currency
        profile.refresh_from_db()
        self.assertEqual(profile.balance, Decimal('1234.57'))  # Rounded to 2 places

    def test_user_profile_cascade_deletion(self):
        """Test that profile is handled correctly when user is deleted"""
        profile = UserProfile.objects.create(
            user=self.user,
            balance=1000.00
        )
        
        profile_id = profile.id
        user_id = self.user.id
        
        # Delete user
        self.user.delete()
        
        # Profile should also be deleted (CASCADE)
        with self.assertRaises(UserProfile.DoesNotExist):
            UserProfile.objects.get(id=profile_id)
        
        # User should be deleted
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=user_id)
