"""
Test institutional data access security.

Verifies that only platform staff (SUPER_ADMIN) can access institutional
subscription data, not YEA government officials.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from accounts.policies import UserPolicy


class InstitutionalDataAccessTest(TestCase):
    """Test that institutional data is properly restricted."""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create users with different roles
        self.super_admin = User.objects.create_user(
            email='super@platform.com',
            username='super_admin',
            password='testpass123',
            role='SUPER_ADMIN',
            phone='+233201111111',
            is_active=True,
            is_verified=True
        )
        
        self.national_admin = User.objects.create_user(
            email='national@yea.gov.gh',
            username='national_admin',
            password='testpass123',
            role='NATIONAL_ADMIN',
            phone='+233201111112',
            is_active=True,
            is_verified=True
        )
        
        self.regional_admin = User.objects.create_user(
            email='regional@yea.gov.gh',
            username='regional_admin',
            password='testpass123',
            role='REGIONAL_ADMIN',
            region='Greater Accra',
            phone='+233201111113',
            is_active=True,
            is_verified=True
        )
    
    def test_is_platform_staff_method(self):
        """Test the is_platform_staff() helper method."""
        # Only SUPER_ADMIN should be platform staff
        self.assertTrue(UserPolicy.is_platform_staff(self.super_admin))
        self.assertFalse(UserPolicy.is_platform_staff(self.national_admin))
        self.assertFalse(UserPolicy.is_platform_staff(self.regional_admin))
    
    def test_super_admin_can_access_institutional_dashboard(self):
        """SUPER_ADMIN should access institutional dashboard."""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get('/api/admin/institutional/dashboard/')
        
        # Should succeed (200) or at least not be forbidden (403)
        self.assertNotEqual(response.status_code, 403)
    
    def test_national_admin_cannot_access_institutional_dashboard(self):
        """NATIONAL_ADMIN should NOT access institutional dashboard."""
        self.client.force_authenticate(user=self.national_admin)
        response = self.client.get('/api/admin/institutional/dashboard/')
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
        self.assertIn('platform administrators', str(response.data).lower())
    
    def test_regional_admin_cannot_access_institutional_dashboard(self):
        """REGIONAL_ADMIN should NOT access institutional dashboard."""
        self.client.force_authenticate(user=self.regional_admin)
        response = self.client.get('/api/admin/institutional/dashboard/')
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_national_admin_cannot_list_subscribers(self):
        """NATIONAL_ADMIN should NOT list institutional subscribers."""
        self.client.force_authenticate(user=self.national_admin)
        response = self.client.get('/api/admin/institutional/subscribers/')
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_super_admin_can_list_subscribers(self):
        """SUPER_ADMIN should list institutional subscribers."""
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get('/api/admin/institutional/subscribers/')
        
        # Should not be forbidden
        self.assertNotEqual(response.status_code, 403)


if __name__ == '__main__':
    import sys
    import os
    import django
    
    # Setup Django
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    django.setup()
    
    # Run tests
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["__main__"])
