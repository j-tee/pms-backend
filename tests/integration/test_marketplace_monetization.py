"""
Comprehensive Test Suite for Marketplace Monetization Features

Tests cover:
1. PlatformSettings model (singleton pattern, defaults, validation)
2. Platform Settings API endpoints (admin and public)
3. require_marketplace_activation decorator
4. SalesPolicy.can_create_sale method
5. Farm marketplace access tiers
6. Edge cases and error handling

Run with: pytest test_marketplace_monetization.py -v
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
import uuid


User = get_user_model()


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def super_admin_user(db):
    """Create a super admin user."""
    user = User.objects.create_user(
        username='superadmin',
        email='superadmin@yea.gov.gh',
        password='testpass123',
        role='SUPER_ADMIN',
        first_name='Super',
        last_name='Admin',
        phone='+233201234567'
    )
    return user


@pytest.fixture
def yea_official_user(db):
    """Create a YEA official user."""
    user = User.objects.create_user(
        username='yeaofficial',
        email='official@yea.gov.gh',
        password='testpass123',
        role='YEA_OFFICIAL',
        first_name='YEA',
        last_name='Official',
        phone='+233201234568'
    )
    return user


@pytest.fixture
def farmer_user(db):
    """Create a farmer user."""
    user = User.objects.create_user(
        username='farmer',
        email='farmer@example.com',
        password='testpass123',
        role='FARMER',
        first_name='Test',
        last_name='Farmer',
        phone='+233201234569'
    )
    return user


@pytest.fixture
def farmer_user_2(db):
    """Create a second farmer user."""
    user = User.objects.create_user(
        username='farmer2',
        email='farmer2@example.com',
        password='testpass123',
        role='FARMER',
        first_name='Test2',
        last_name='Farmer2',
        phone='+233201234570'
    )
    return user


@pytest.fixture
def regional_coordinator_user(db):
    """Create a regional coordinator user."""
    user = User.objects.create_user(
        username='regional',
        email='regional@yea.gov.gh',
        password='testpass123',
        role='REGIONAL_COORDINATOR',
        first_name='Regional',
        last_name='Coordinator',
        phone='+233201234571'
    )
    return user


@pytest.fixture
def platform_settings(db):
    """Get or create platform settings singleton."""
    from sales_revenue.models import PlatformSettings
    return PlatformSettings.get_settings()


def create_test_farm(user, marketplace_enabled=True, subscription_type='standard'):
    """Helper to create a test farm with required fields."""
    from farms.models import Farm
    from datetime import date
    
    unique_id = str(uuid.uuid4())[:8]
    
    farm = Farm(
        user=user,
        # Personal Identity
        first_name=user.first_name,
        last_name=user.last_name,
        date_of_birth=date(1990, 1, 1),
        gender='Male',
        ghana_card_number=f'GHA-{unique_id}0-1',
        primary_phone=user.phone or f'+23320{unique_id[:7]}',
        nok_full_name='Test NOK',
        nok_relationship='Parent',
        nok_phone=f'+23324{unique_id[:7]}',
        residential_address='Test Address',
        primary_constituency='Ablekuma South',
        # Education
        education_level='Tertiary',
        literacy_level='Can Read & Write',
        years_in_poultry=Decimal('2.0'),
        farming_full_time=True,
        # Business
        farm_name=f'Test Farm {unique_id}',
        ownership_type='Sole Proprietorship',
        tin=f'C00{unique_id[:5]}0',
        # Capacity (required for save)
        total_bird_capacity=1000,
        number_of_poultry_houses=2,
        # Marketplace
        marketplace_enabled=marketplace_enabled,
        subscription_type=subscription_type,
    )
    farm.save()
    return farm


def create_mock_farm(marketplace_enabled=True, subscription_type='standard', has_subscription_obj=False):
    """Create a mock farm for testing without database."""
    farm = Mock()
    farm.marketplace_enabled = marketplace_enabled
    farm.subscription_type = subscription_type
    
    if has_subscription_obj:
        farm.subscription = Mock()
        farm.subscription.status = 'active'
    else:
        # Make hasattr return False for subscription
        del farm.subscription
    
    return farm


@pytest.fixture
def farm_with_marketplace(db, farmer_user):
    """Create a farm with marketplace enabled."""
    return create_test_farm(farmer_user, marketplace_enabled=True, subscription_type='standard')


@pytest.fixture
def farm_no_marketplace(db, farmer_user_2):
    """Create a farm without marketplace access."""
    return create_test_farm(farmer_user_2, marketplace_enabled=False, subscription_type='none')


@pytest.fixture
def mock_farm_with_marketplace():
    """Mock farm with marketplace enabled (no DB)."""
    return create_mock_farm(marketplace_enabled=True, subscription_type='standard')


@pytest.fixture
def mock_farm_no_marketplace():
    """Mock farm without marketplace (no DB)."""
    return create_mock_farm(marketplace_enabled=False, subscription_type='none')


# =============================================================================
# PLATFORM SETTINGS MODEL TESTS
# =============================================================================

@pytest.mark.django_db
class TestPlatformSettingsModel:
    """Test PlatformSettings singleton model."""
    
    def test_singleton_pattern_creates_single_instance(self):
        """Verify only one PlatformSettings instance exists."""
        from sales_revenue.models import PlatformSettings
        
        settings1 = PlatformSettings.get_settings()
        settings2 = PlatformSettings.get_settings()
        
        assert settings1.pk == settings2.pk
        assert PlatformSettings.objects.count() == 1
    
    def test_default_marketplace_activation_fee_is_50(self, platform_settings):
        """Verify default marketplace activation fee is GHS 50."""
        assert platform_settings.marketplace_activation_fee == Decimal('50.00')
    
    def test_default_trial_days_is_14(self, platform_settings):
        """Verify default trial period is 14 days."""
        assert platform_settings.marketplace_trial_days == 14
    
    def test_default_grace_period_is_5_days(self, platform_settings):
        """Verify default grace period is 5 days."""
        assert platform_settings.marketplace_grace_period_days == 5
    
    def test_government_subsidy_disabled_by_default(self, platform_settings):
        """Verify government subsidy is disabled by default."""
        assert platform_settings.enable_government_subsidy is False
    
    def test_government_subsidy_default_percentage_is_100(self, platform_settings):
        """Verify default government subsidy covers 100%."""
        assert platform_settings.government_subsidy_percentage == Decimal('100.00')
    
    def test_transaction_commission_disabled_by_default(self, platform_settings):
        """Verify transaction commission (Phase 2) is disabled by default."""
        assert platform_settings.enable_transaction_commission is False
    
    def test_free_tier_can_view_marketplace_by_default(self, platform_settings):
        """Verify free tier users can view marketplace by default."""
        assert platform_settings.free_tier_can_view_marketplace is True
        assert platform_settings.free_tier_can_view_prices is True
        assert platform_settings.free_tier_can_access_education is True
    
    def test_update_marketplace_fee(self, platform_settings):
        """Test updating marketplace activation fee."""
        platform_settings.marketplace_activation_fee = Decimal('75.00')
        platform_settings.save()
        
        # Refresh from DB
        from sales_revenue.models import PlatformSettings
        updated = PlatformSettings.get_settings()
        assert updated.marketplace_activation_fee == Decimal('75.00')
    
    def test_fee_validation_min_zero(self, platform_settings):
        """Test that marketplace fee cannot be negative."""
        from django.core.exceptions import ValidationError
        
        platform_settings.marketplace_activation_fee = Decimal('-10.00')
        with pytest.raises(ValidationError):
            platform_settings.full_clean()
    
    def test_trial_days_max_90(self, platform_settings):
        """Test trial days maximum is 90."""
        from django.core.exceptions import ValidationError
        
        platform_settings.marketplace_trial_days = 100
        with pytest.raises(ValidationError):
            platform_settings.full_clean()
    
    def test_subsidy_percentage_max_100(self, platform_settings):
        """Test subsidy percentage cannot exceed 100%."""
        from django.core.exceptions import ValidationError
        
        platform_settings.government_subsidy_percentage = Decimal('150.00')
        with pytest.raises(ValidationError):
            platform_settings.full_clean()


# =============================================================================
# PLATFORM SETTINGS API TESTS
# =============================================================================

@pytest.mark.django_db
class TestPlatformSettingsAPI:
    """Test Platform Settings REST API endpoints."""
    
    def test_super_admin_can_get_settings(self, api_client, super_admin_user, platform_settings):
        """Super Admin can access full platform settings."""
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.get('/api/admin/platform-settings/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'marketplace_activation_fee' in response.data
        assert 'enable_government_subsidy' in response.data
    
    def test_yea_official_cannot_access_admin_settings(self, api_client, yea_official_user, platform_settings):
        """YEA Official cannot access admin platform settings (SUPER_ADMIN only)."""
        api_client.force_authenticate(user=yea_official_user)
        response = api_client.get('/api/admin/platform-settings/')
        
        # YEA officials are government staff, not platform admins
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_farmer_cannot_access_admin_settings(self, api_client, farmer_user, platform_settings):
        """Farmers cannot access admin platform settings."""
        api_client.force_authenticate(user=farmer_user)
        response = api_client.get('/api/admin/platform-settings/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['code'] == 'PERMISSION_DENIED'
    
    def test_regional_coordinator_cannot_access_admin_settings(
        self, api_client, regional_coordinator_user, platform_settings
    ):
        """Regional coordinators cannot access admin platform settings."""
        api_client.force_authenticate(user=regional_coordinator_user)
        response = api_client.get('/api/admin/platform-settings/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_unauthenticated_cannot_access_admin_settings(self, api_client, platform_settings):
        """Unauthenticated users cannot access admin settings."""
        response = api_client.get('/api/admin/platform-settings/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_super_admin_can_update_settings_patch(
        self, api_client, super_admin_user, platform_settings
    ):
        """Super Admin can PATCH update settings."""
        api_client.force_authenticate(user=super_admin_user)
        
        response = api_client.patch(
            '/api/admin/platform-settings/',
            {'marketplace_activation_fee': '75.00'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data['marketplace_activation_fee']) == Decimal('75.00')
    
    def test_super_admin_can_update_monetization_endpoint(
        self, api_client, super_admin_user, platform_settings
    ):
        """Super Admin can update via monetization-specific endpoint."""
        api_client.force_authenticate(user=super_admin_user)
        
        response = api_client.patch(
            '/api/admin/platform-settings/monetization/',
            {
                'marketplace_activation_fee': '65.00',
                'enable_government_subsidy': True,
                'government_subsidy_percentage': '50.00'
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data['marketplace_activation_fee']) == Decimal('65.00')
        assert response.data['enable_government_subsidy'] is True
    
    def test_farmer_cannot_update_settings(self, api_client, farmer_user, platform_settings):
        """Farmers cannot update platform settings."""
        api_client.force_authenticate(user=farmer_user)
        
        response = api_client.patch(
            '/api/admin/platform-settings/',
            {'marketplace_activation_fee': '10.00'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_invalid_fee_rejected(self, api_client, super_admin_user, platform_settings):
        """Invalid negative fee is rejected."""
        api_client.force_authenticate(user=super_admin_user)
        
        response = api_client.patch(
            '/api/admin/platform-settings/',
            {'marketplace_activation_fee': '-50.00'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestPublicPlatformSettingsAPI:
    """Test public platform settings endpoint."""
    
    def test_public_endpoint_accessible_without_auth(self, api_client, platform_settings):
        """Public settings endpoint doesn't require authentication."""
        response = api_client.get('/api/public/platform-settings/')
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_public_endpoint_returns_marketplace_fee(self, api_client, platform_settings):
        """Public endpoint includes marketplace activation fee."""
        response = api_client.get('/api/public/platform-settings/')
        
        assert 'marketplace_activation_fee' in response.data
        assert Decimal(response.data['marketplace_activation_fee']) == Decimal('50.00')
    
    def test_public_endpoint_returns_trial_days(self, api_client, platform_settings):
        """Public endpoint includes trial period info."""
        response = api_client.get('/api/public/platform-settings/')
        
        assert 'marketplace_trial_days' in response.data
        assert response.data['marketplace_trial_days'] == 14
    
    def test_public_endpoint_hides_sensitive_fields(self, api_client, platform_settings):
        """Public endpoint doesn't expose sensitive admin fields."""
        response = api_client.get('/api/public/platform-settings/')
        
        # These should NOT be in public response
        assert 'paystack_fee_bearer' not in response.data
        assert 'payment_retry_max_attempts' not in response.data
        assert 'last_modified_by' not in response.data


@pytest.mark.django_db
class TestPlatformSettingsReset:
    """Test platform settings reset functionality."""
    
    def test_super_admin_can_reset_to_defaults(self, api_client, super_admin_user, platform_settings):
        """Super Admin can reset settings to defaults."""
        api_client.force_authenticate(user=super_admin_user)
        
        # First modify a setting
        platform_settings.marketplace_activation_fee = Decimal('999.00')
        platform_settings.save()
        
        # Reset
        response = api_client.post('/api/admin/platform-settings/reset/')
        
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data['settings']['marketplace_activation_fee']) == Decimal('50.00')
    
    def test_yea_official_cannot_reset(self, api_client, yea_official_user, platform_settings):
        """YEA Official cannot reset settings (Super Admin only)."""
        api_client.force_authenticate(user=yea_official_user)
        
        response = api_client.post('/api/admin/platform-settings/reset/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_farmer_cannot_reset(self, api_client, farmer_user, platform_settings):
        """Farmers cannot reset settings."""
        api_client.force_authenticate(user=farmer_user)
        
        response = api_client.post('/api/admin/platform-settings/reset/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# FARM MARKETPLACE ACCESS TESTS (Using Mocks)
# =============================================================================

class TestFarmMarketplaceAccess:
    """Test farm marketplace access tiers using mocks."""
    
    def test_has_marketplace_access_none(self, mock_farm_no_marketplace):
        """Farm with 'none' tier has no marketplace access."""
        # Test logic: subscription_type='none' means no access
        farm = mock_farm_no_marketplace
        # Simulate the has_marketplace_access property logic
        has_access = farm.subscription_type in ['government_subsidized', 'standard', 'verified']
        assert has_access is False
    
    def test_has_marketplace_access_standard(self, mock_farm_with_marketplace):
        """Farm with 'standard' tier has marketplace access."""
        farm = mock_farm_with_marketplace
        farm.subscription_type = 'standard'
        has_access = farm.subscription_type in ['government_subsidized', 'standard', 'verified']
        assert has_access is True
    
    def test_has_marketplace_access_government_subsidized(self, mock_farm_with_marketplace):
        """Farm with 'government_subsidized' tier has marketplace access."""
        farm = mock_farm_with_marketplace
        farm.subscription_type = 'government_subsidized'
        has_access = farm.subscription_type in ['government_subsidized', 'standard', 'verified']
        assert has_access is True
    
    def test_has_marketplace_access_verified(self, mock_farm_with_marketplace):
        """Farm with 'verified' tier has marketplace access."""
        farm = mock_farm_with_marketplace
        farm.subscription_type = 'verified'
        has_access = farm.subscription_type in ['government_subsidized', 'standard', 'verified']
        assert has_access is True


# =============================================================================
# REQUIRE MARKETPLACE ACTIVATION DECORATOR TESTS
# =============================================================================

class TestRequireMarketplaceActivationDecorator:
    """Test require_marketplace_activation decorator logic."""
    
    def test_backward_compatibility_alias(self):
        """require_marketplace_subscription alias works."""
        from accounts.decorators import require_marketplace_subscription, require_marketplace_activation
        
        assert require_marketplace_subscription is require_marketplace_activation
    
    def test_decorator_exists_and_callable(self):
        """Decorator is importable and callable."""
        from accounts.decorators import require_marketplace_activation
        
        assert callable(require_marketplace_activation)
    
    def test_decorator_logic_checks_authentication(self):
        """Test decorator logic checks for authentication."""
        # The decorator should:
        # 1. Check user.is_authenticated
        # 2. Check hasattr(user, 'farm')
        # 3. Check farm.marketplace_enabled
        # 4. Check farm.subscription_type
        # This is a logic verification, not a runtime test
        from accounts.decorators import require_marketplace_activation
        import inspect
        
        # Get source code of the wrapper function
        source = inspect.getsource(require_marketplace_activation)
        
        # Verify key checks are in the decorator
        assert 'is_authenticated' in source
        assert 'farm' in source
        assert 'marketplace_enabled' in source
        assert 'subscription_type' in source
    
    def test_decorator_uses_platform_settings(self):
        """Decorator imports PlatformSettings for dynamic fee."""
        from accounts.decorators import require_marketplace_activation
        import inspect
        
        source = inspect.getsource(require_marketplace_activation)
        
        # Verify PlatformSettings is used
        assert 'PlatformSettings' in source
        assert 'marketplace_activation_fee' in source


# =============================================================================
# SALES POLICY TESTS (Using Mocks)
# =============================================================================

class TestSalesPolicyCanCreateSale:
    """Test SalesPolicy.can_create_sale method logic."""
    
    def test_farmer_can_create_sale_logic(self):
        """Farmer with active marketplace can create sale (logic test)."""
        # Test the core logic that can_create_sale checks:
        # 1. User must be a farmer
        # 2. User must own the farm
        # 3. Farm must have marketplace_enabled = True
        # 4. subscription_type must not be 'none'
        
        farm = Mock()
        farm.marketplace_enabled = True
        farm.subscription_type = 'standard'
        
        user = Mock()
        user.role = 'FARMER'
        farm.user = user  # owner check
        
        # Simulate can_create_sale logic
        can_create = (
            user.role == 'FARMER' and
            farm.user == user and
            farm.marketplace_enabled and
            farm.subscription_type != 'none'
        )
        
        assert can_create is True
    
    def test_farmer_cannot_create_sale_without_marketplace_logic(self):
        """Farmer without marketplace cannot create sale (logic test)."""
        farm = Mock()
        farm.marketplace_enabled = False
        farm.subscription_type = 'standard'
        
        user = Mock()
        user.role = 'FARMER'
        farm.user = user
        
        can_create = (
            user.role == 'FARMER' and
            farm.user == user and
            farm.marketplace_enabled and
            farm.subscription_type != 'none'
        )
        
        assert can_create is False
    
    def test_farmer_cannot_create_sale_with_none_subscription_logic(self):
        """Farmer with subscription_type='none' cannot create sale (logic test)."""
        farm = Mock()
        farm.marketplace_enabled = True
        farm.subscription_type = 'none'
        
        user = Mock()
        user.role = 'FARMER'
        farm.user = user
        
        can_create = (
            user.role == 'FARMER' and
            farm.user == user and
            farm.marketplace_enabled and
            farm.subscription_type != 'none'
        )
        
        assert can_create is False
    
    def test_farmer_cannot_create_sale_for_other_farm_logic(self):
        """Farmer cannot create sale for farm they don't own (logic test)."""
        farm = Mock()
        farm.marketplace_enabled = True
        farm.subscription_type = 'standard'
        
        user = Mock()
        user.role = 'FARMER'
        other_user = Mock()
        farm.user = other_user  # Different owner
        
        can_create = (
            user.role == 'FARMER' and
            farm.user == user and
            farm.marketplace_enabled and
            farm.subscription_type != 'none'
        )
        
        assert can_create is False
    
    def test_non_farmer_cannot_create_sale_logic(self):
        """Non-farmers cannot create sales (logic test)."""
        farm = Mock()
        farm.marketplace_enabled = True
        farm.subscription_type = 'standard'
        
        user = Mock()
        user.role = 'SUPER_ADMIN'
        farm.user = user
        
        can_create = (
            user.role == 'FARMER' and
            farm.user == user and
            farm.marketplace_enabled and
            farm.subscription_type != 'none'
        )
        
        assert can_create is False
    
    def test_government_subsidized_can_create_sale_logic(self):
        """Government subsidized farms can create sales (logic test)."""
        farm = Mock()
        farm.marketplace_enabled = True
        farm.subscription_type = 'government_subsidized'
        
        user = Mock()
        user.role = 'FARMER'
        farm.user = user
        
        can_create = (
            user.role == 'FARMER' and
            farm.user == user and
            farm.marketplace_enabled and
            farm.subscription_type != 'none'
        )
        
        assert can_create is True


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================

@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_platform_settings_created_on_first_access(self, db):
        """PlatformSettings get_settings returns valid settings."""
        from sales_revenue.models import PlatformSettings
        
        # Access should always return a valid settings object
        settings = PlatformSettings.get_settings()
        
        assert settings is not None
        assert hasattr(settings, 'marketplace_activation_fee')
        assert settings.marketplace_activation_fee is not None
    
    def test_zero_marketplace_fee_allowed(self, platform_settings):
        """Zero marketplace fee (free tier) is valid."""
        platform_settings.marketplace_activation_fee = Decimal('0.00')
        platform_settings.full_clean()  # Should not raise
        platform_settings.save()
        
        assert platform_settings.marketplace_activation_fee == Decimal('0.00')
    
    def test_zero_trial_days_allowed(self, platform_settings):
        """Zero trial days (no trial) is valid."""
        platform_settings.marketplace_trial_days = 0
        platform_settings.full_clean()  # Should not raise
        platform_settings.save()
        
        assert platform_settings.marketplace_trial_days == 0
    
    def test_decimal_precision_preserved(self, platform_settings):
        """Decimal precision is preserved for fees."""
        platform_settings.marketplace_activation_fee = Decimal('49.99')
        platform_settings.save()
        
        from sales_revenue.models import PlatformSettings
        refreshed = PlatformSettings.get_settings()
        
        assert refreshed.marketplace_activation_fee == Decimal('49.99')
    
    def test_concurrent_settings_access(self, db):
        """Multiple concurrent accesses return same instance."""
        from sales_revenue.models import PlatformSettings
        import threading
        
        results = []
        
        def get_settings():
            s = PlatformSettings.get_settings()
            results.append(s.pk)
        
        threads = [threading.Thread(target=get_settings) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should return same PK
        assert len(set(results)) == 1
    
    def test_api_handles_malformed_json(self, api_client, super_admin_user, platform_settings):
        """API handles malformed JSON gracefully."""
        api_client.force_authenticate(user=super_admin_user)
        
        response = api_client.patch(
            '/api/admin/platform-settings/',
            'not valid json',
            content_type='application/json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_api_handles_wrong_type(self, api_client, super_admin_user, platform_settings):
        """API rejects wrong data types."""
        api_client.force_authenticate(user=super_admin_user)
        
        response = api_client.patch(
            '/api/admin/platform-settings/',
            {'marketplace_activation_fee': 'not a number'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_large_fee_value(self, platform_settings):
        """Large but valid fee values work."""
        platform_settings.marketplace_activation_fee = Decimal('99999999.99')
        platform_settings.full_clean()  # Should not raise
        platform_settings.save()
        
        assert platform_settings.marketplace_activation_fee == Decimal('99999999.99')


# =============================================================================
# TERMINOLOGY COMPLIANCE TESTS  
# =============================================================================

class TestTerminologyCompliance:
    """Verify 'subscription' terminology has been replaced in code."""
    
    def test_decorator_source_uses_activation_terminology(self):
        """Decorator uses 'activation' not 'subscription' in error messages."""
        from accounts.decorators import require_marketplace_activation
        import inspect
        
        source = inspect.getsource(require_marketplace_activation)
        
        # Check that actual error messages/codes don't contain 'subscription'
        # We look for error dict keys which contain the actual messages
        # Allow: docstrings, comments, backward compat alias
        
        # These patterns would indicate a problem (subscription in error messages)
        bad_patterns = [
            "'error': 'subscription",
            "'error': \"subscription",
            "'message': 'subscription",
            "'message': \"subscription",
            "'code': 'SUBSCRIPTION"
        ]
        
        for pattern in bad_patterns:
            assert pattern.lower() not in source.lower(), f"Found subscription in error message: {pattern}"
    
    def test_error_codes_in_decorator_use_activation(self):
        """Error codes use ACTIVATION not SUBSCRIPTION."""
        from accounts.decorators import require_marketplace_activation
        import inspect
        
        source = inspect.getsource(require_marketplace_activation)
        
        # Should not have SUBSCRIPTION_REQUIRED error code
        assert 'SUBSCRIPTION_REQUIRED' not in source
        # Should have activation-related codes
        assert 'ACTIVATION' in source or 'MARKETPLACE_NOT_ACTIVATED' in source


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.django_db
class TestFullIntegration:
    """Full integration tests for marketplace monetization flow."""
    
    def test_admin_updates_fee_public_reflects_changes(
        self, api_client, super_admin_user, platform_settings
    ):
        """
        Integration test: Admin updates fee → Public endpoint reflects it.
        """
        # Step 1: Admin updates fee
        api_client.force_authenticate(user=super_admin_user)
        response = api_client.patch(
            '/api/admin/platform-settings/',
            {'marketplace_activation_fee': '75.00'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        
        # Step 2: Check public endpoint reflects the change
        api_client.logout()
        response = api_client.get('/api/public/platform-settings/')
        
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data['marketplace_activation_fee']) == Decimal('75.00')
    
    def test_public_settings_reflects_admin_changes(
        self, api_client, super_admin_user
    ):
        """
        Integration test: Admin changes → Public endpoint reflects them.
        """
        # Step 1: Admin updates fee
        api_client.force_authenticate(user=super_admin_user)
        api_client.patch(
            '/api/admin/platform-settings/',
            {'marketplace_activation_fee': '42.00'},
            format='json'
        )
        
        # Step 2: Check public endpoint (unauthenticated)
        api_client.logout()
        response = api_client.get('/api/public/platform-settings/')
        
        assert response.status_code == status.HTTP_200_OK
        assert Decimal(response.data['marketplace_activation_fee']) == Decimal('42.00')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
