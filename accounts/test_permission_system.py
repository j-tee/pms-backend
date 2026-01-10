"""
Comprehensive tests for Permission Management System.

Tests all permission management endpoints, role-based access control,
jurisdiction scoping, and permission evaluation logic.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from accounts.models import User
from accounts.roles import Permission, UserPermission
from farms.models import Farm
from subscriptions.models import Subscription

User = get_user_model()


@pytest.fixture
def api_client():
    """API client for making requests."""
    return APIClient()


@pytest.fixture
def super_admin(db):
    """Create a super admin user."""
    user = User.objects.create_user(
        username='super_admin',
        email='super@admin.com',
        password='testpass123',
        first_name='Super',
        last_name='Admin',
        role='SUPER_ADMIN',
        phone='+233240000001',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def national_admin(db):
    """Create a national admin user."""
    user = User.objects.create_user(
        username='national_admin',
        email='national@admin.com',
        password='testpass123',
        first_name='National',
        last_name='Admin',
        role='NATIONAL_ADMIN',
        phone='+233240000002',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def national_staff(db):
    """Create a national staff user."""
    user = User.objects.create_user(
        username='national_staff',
        email='national@staff.com',
        password='testpass123',
        first_name='National',
        last_name='Staff',
        role='NATIONAL_STAFF',
        phone='+233240000003',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def regional_admin(db):
    """Create a regional admin user."""
    user = User.objects.create_user(
        username='regional_admin',
        email='regional@admin.com',
        password='testpass123',
        first_name='Regional',
        last_name='Admin',
        role='REGIONAL_ADMIN',
        region='Greater Accra',
        phone='+233240000004',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def regional_staff(db):
    """Create a regional staff user."""
    user = User.objects.create_user(
        username='regional_staff',
        email='regional@staff.com',
        password='testpass123',
        first_name='Regional',
        last_name='Staff',
        role='REGIONAL_STAFF',
        region='Greater Accra',
        phone='+233240000005',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def regional_staff_ashanti(db):
    """Create a regional staff user in a different region."""
    user = User.objects.create_user(
        username='regional_staff_ashanti',
        email='regional2@staff.com',
        password='testpass123',
        first_name='Regional Ashanti',
        last_name='Staff',
        role='REGIONAL_STAFF',
        region='Ashanti',
        phone='+233240000006',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def constituency_admin(db):
    """Create a constituency admin user."""
    user = User.objects.create_user(
        username='constituency_admin',
        email='constituency@admin.com',
        password='testpass123',
        first_name='Constituency',
        last_name='Admin',
        role='CONSTITUENCY_ADMIN',
        region='Greater Accra',
        constituency='Ablekuma Central',
        phone='+233240000007',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def constituency_staff(db):
    """Create a constituency staff user."""
    user = User.objects.create_user(
        username='constituency_staff',
        email='constituency@staff.com',
        password='testpass123',
        first_name='Constituency',
        last_name='Staff',
        role='CONSTITUENCY_STAFF',
        region='Greater Accra',
        constituency='Ablekuma Central',
        phone='+233240000008',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def extension_officer(db):
    """Create an extension officer."""
    user = User.objects.create_user(
        username='extension_officer',
        email='extension@officer.com',
        password='testpass123',
        first_name='Extension',
        last_name='Officer',
        role='EXTENSION_OFFICER',
        region='Greater Accra',
        constituency='Ablekuma Central',
        phone='+233240000009',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.fixture
def farmer(db):
    """Create a farmer user."""
    user = User.objects.create_user(
        username='test_farmer',
        email='farmer@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Farmer',
        role='FARMER',
        phone='+233240000010',
        is_active=True,
        is_verified=True
    )
    return user


@pytest.mark.django_db
class TestPermissionListEndpoint:
    """Test GET /api/admin/permissions/"""
    
    def test_list_permissions_as_super_admin(self, api_client, super_admin):
        """Super admin can view all permissions."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/permissions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'permissions' in response.data
        assert 'total_count' in response.data
        assert response.data['total_count'] > 0
        
        # Check categories exist
        permissions = response.data['permissions']
        expected_categories = [
            'user_management', 'farm_management', 'batch_management',
            'application_review', 'analytics', 'financial',
            'marketplace', 'content', 'system'
        ]
        for category in expected_categories:
            assert category in permissions
    
    def test_list_permissions_as_national_admin(self, api_client, national_admin):
        """National admin can view permissions."""
        api_client.force_authenticate(user=national_admin)
        response = api_client.get('/api/admin/permissions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'permissions' in response.data
    
    def test_list_permissions_as_farmer_forbidden(self, api_client, farmer):
        """Farmers cannot view permissions."""
        api_client.force_authenticate(user=farmer)
        response = api_client.get('/api/admin/permissions/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['code'] == 'ADMIN_REQUIRED'
    
    def test_list_permissions_structure(self, api_client, super_admin):
        """Check permission structure is correct."""
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/permissions/')
        
        # Pick first category and check structure
        permissions = response.data['permissions']
        first_category = list(permissions.keys())[0]
        first_perm = permissions[first_category][0]
        
        assert 'codename' in first_perm
        assert 'name' in first_perm
        assert 'description' in first_perm


@pytest.mark.django_db
class TestManageableUsersEndpoint:
    """Test GET /api/admin/permissions/manageable-users/"""
    
    def test_super_admin_sees_all_except_super_admins(
        self, api_client, super_admin, national_admin, regional_admin, 
        national_staff, farmer
    ):
        """Super admin sees all users except other super admins."""
        # Create another super admin
        other_super = User.objects.create_user(
            username='other_super',
            email='other_super@admin.com',
            password='testpass123',
            role='SUPER_ADMIN',
            phone='+233240000099',
        )
        
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/admin/permissions/manageable-users/')
        
        assert response.status_code == status.HTTP_200_OK
        user_ids = [u['id'] for u in response.data['users']]
        
        # Should see themselves
        assert str(super_admin.id) in user_ids
        # Should see other admins and staff
        assert str(national_admin.id) in user_ids
        assert str(regional_admin.id) in user_ids
        assert str(national_staff.id) in user_ids
        # Should NOT see other super admin
        assert str(other_super.id) not in user_ids
    
    def test_national_admin_sees_national_and_below(
        self, api_client, national_admin, national_staff, regional_admin,
        regional_staff, super_admin
    ):
        """National admin sees national staff and all below, not super admins."""
        api_client.force_authenticate(user=national_admin)
        response = api_client.get('/api/admin/permissions/manageable-users/')
        
        assert response.status_code == status.HTTP_200_OK
        user_ids = [u['id'] for u in response.data['users']]
        
        # Should see national staff and below
        assert str(national_staff.id) in user_ids
        assert str(regional_admin.id) in user_ids
        assert str(regional_staff.id) in user_ids
        # Should NOT see super admin
        assert str(super_admin.id) not in user_ids
    
    def test_regional_admin_only_sees_own_region(
        self, api_client, regional_admin, regional_staff, 
        regional_staff_ashanti, constituency_staff
    ):
        """Regional admin only sees users in their region."""
        api_client.force_authenticate(user=regional_admin)
        response = api_client.get('/api/admin/permissions/manageable-users/')
        
        assert response.status_code == status.HTTP_200_OK
        user_ids = [u['id'] for u in response.data['users']]
        
        # Should see users in Greater Accra
        assert str(regional_staff.id) in user_ids
        assert str(constituency_staff.id) in user_ids
        # Should NOT see users in other regions
        assert str(regional_staff_ashanti.id) not in user_ids
    
    def test_farmer_cannot_access(self, api_client, farmer):
        """Farmers cannot access manageable users endpoint."""
        api_client.force_authenticate(user=farmer)
        response = api_client.get('/api/admin/permissions/manageable-users/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestUserPermissionsEndpoint:
    """Test GET /api/admin/users/<id>/permissions/"""
    
    def test_get_user_permissions_success(self, api_client, national_admin, national_staff):
        """Admin can view staff's permissions."""
        api_client.force_authenticate(user=national_admin)
        response = api_client.get(f'/api/admin/users/{national_staff.id}/permissions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['user_id'] == str(national_staff.id)
        assert response.data['user_role'] == 'NATIONAL_STAFF'
        assert 'permissions' in response.data
        assert response.data['can_manage'] is True
    
    def test_permission_source_types(self, api_client, national_admin, national_staff):
        """Check that permission sources are correctly identified."""
        api_client.force_authenticate(user=national_admin)
        response = api_client.get(f'/api/admin/users/{national_staff.id}/permissions/')
        
        permissions = response.data['permissions']
        
        # Should have various source types
        sources = [p['source'] for p in permissions.values()]
        assert 'default' in sources  # Staff have default permissions
    
    def test_cannot_view_higher_level_permissions(self, api_client, regional_admin, national_admin):
        """Regional admin cannot view national admin's permissions."""
        api_client.force_authenticate(user=regional_admin)
        response = api_client.get(f'/api/admin/users/{national_admin.id}/permissions/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_cannot_view_different_region(
        self, api_client, regional_admin, regional_staff_ashanti
    ):
        """Regional admin cannot view users from other regions."""
        api_client.force_authenticate(user=regional_admin)
        response = api_client.get(f'/api/admin/users/{regional_staff_ashanti.id}/permissions/')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestGrantPermission:
    """Test POST /api/admin/users/<id>/permissions/grant/"""
    
    def test_grant_permission_success(self, api_client, national_admin, national_staff):
        """Admin can grant permission to staff."""
        api_client.force_authenticate(user=national_admin)
        
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {'permission': 'create_batches'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['permission'] == 'create_batches'
        assert 'granted successfully' in response.data['message']
        
        # Verify in database
        assert UserPermission.objects.filter(
            user=national_staff,
            permission__codename='create_batches',
            is_granted=True
        ).exists()
    
    def test_cannot_grant_to_higher_role(self, api_client, regional_admin, national_admin):
        """Regional admin cannot grant permissions to national admin."""
        api_client.force_authenticate(user=regional_admin)
        
        response = api_client.post(
            f'/api/admin/users/{national_admin.id}/permissions/grant/',
            {'permission': 'view_farms'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'GRANT_FAILED' in response.data['code']
    
    def test_cannot_grant_outside_jurisdiction(
        self, api_client, regional_admin, regional_staff_ashanti
    ):
        """Regional admin cannot grant permissions to users in other regions."""
        api_client.force_authenticate(user=regional_admin)
        
        response = api_client.post(
            f'/api/admin/users/{regional_staff_ashanti.id}/permissions/grant/',
            {'permission': 'view_farms'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_grant_invalid_permission(self, api_client, national_admin, national_staff):
        """Cannot grant non-existent permission."""
        api_client.force_authenticate(user=national_admin)
        
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {'permission': 'nonexistent_permission'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestRevokePermission:
    """Test POST /api/admin/users/<id>/permissions/revoke/"""
    
    def test_revoke_permission_success(self, api_client, national_admin, national_staff):
        """Admin can revoke permission from staff."""
        # First grant a permission
        api_client.force_authenticate(user=national_admin)
        api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {'permission': 'create_batches'},
            format='json'
        )
        
        # Now revoke it
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/revoke/',
            {'permission': 'create_batches'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'revoked successfully' in response.data['message']
        
        # Verify in database
        perm = UserPermission.objects.get(
            user=national_staff,
            permission__codename='create_batches'
        )
        assert perm.is_granted is False
    
    def test_revoke_default_permission(self, api_client, national_admin, national_staff):
        """Admin can revoke a default permission."""
        api_client.force_authenticate(user=national_admin)
        
        # National staff have 'view_users' by default
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/revoke/',
            {'permission': 'view_users'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Check it's explicitly revoked
        assert UserPermission.objects.filter(
            user=national_staff,
            permission__codename='view_users',
            is_granted=False
        ).exists()


@pytest.mark.django_db
class TestBulkUpdatePermissions:
    """Test POST /api/admin/users/<id>/permissions/"""
    
    def test_bulk_update_success(self, api_client, national_admin, national_staff):
        """Admin can bulk update multiple permissions."""
        api_client.force_authenticate(user=national_admin)
        
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/',
            {
                'permissions': {
                    'create_batches': True,
                    'edit_batches': True,
                    'publish_batches': False,
                }
            },
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'updated' in response.data
        assert len(response.data['updated']) == 3
    
    def test_bulk_update_partial_success(self, api_client, national_admin, national_staff):
        """Bulk update succeeds for valid permissions, reports errors for invalid."""
        api_client.force_authenticate(user=national_admin)
        
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/',
            {
                'permissions': {
                    'create_batches': True,
                    'invalid_perm': True,  # This should fail
                    'edit_batches': True,
                }
            },
            format='json'
        )
        
        # Should still return 200 with partial success
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['updated']) == 2  # Only valid ones
        assert len(response.data['errors']) > 0  # Should report invalid_perm
    
    def test_bulk_update_invalid_format(self, api_client, national_admin, national_staff):
        """Bulk update fails with invalid format."""
        api_client.force_authenticate(user=national_admin)
        
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/',
            {'permissions': 'not_a_dict'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'INVALID_FORMAT' in response.data['code']


@pytest.mark.django_db
class TestResetPermission:
    """Test POST /api/admin/users/<id>/permissions/reset/"""
    
    def test_reset_single_permission(self, api_client, national_admin, national_staff):
        """Admin can reset a single permission to default."""
        api_client.force_authenticate(user=national_admin)
        
        # Grant a permission
        api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {'permission': 'create_batches'},
            format='json'
        )
        
        # Verify it exists
        assert UserPermission.objects.filter(
            user=national_staff,
            permission__codename='create_batches'
        ).exists()
        
        # Reset it
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/reset/',
            {'permission': 'create_batches'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert 'reset to default' in response.data['message']
        
        # Verify it's removed
        assert not UserPermission.objects.filter(
            user=national_staff,
            permission__codename='create_batches'
        ).exists()
    
    def test_reset_all_permissions(self, api_client, national_admin, national_staff):
        """Admin can reset all permissions to default."""
        api_client.force_authenticate(user=national_admin)
        
        # Grant multiple permissions
        for perm in ['create_batches', 'edit_batches', 'publish_batches']:
            api_client.post(
                f'/api/admin/users/{national_staff.id}/permissions/grant/',
                {'permission': perm},
                format='json'
            )
        
        # Verify they exist
        assert UserPermission.objects.filter(user=national_staff).count() == 3
        
        # Reset all
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/reset/',
            {'all': True},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['permissions_cleared'] == 3
        
        # Verify all removed
        assert UserPermission.objects.filter(user=national_staff).count() == 0


@pytest.mark.django_db
class TestPermissionEvaluation:
    """Test that permissions are evaluated correctly based on source."""
    
    def test_implicit_permissions_cannot_be_revoked(
        self, api_client, national_admin, regional_admin
    ):
        """Admin implicit permissions cannot be revoked."""
        api_client.force_authenticate(user=national_admin)
        
        # Try to revoke a permission that regional admin has implicitly
        response = api_client.post(
            f'/api/admin/users/{regional_admin.id}/permissions/revoke/',
            {'permission': 'view_farms'},  # Regional admins have this implicitly
            format='json'
        )
        
        # Should fail because it's implicit
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_explicit_grant_overrides_default(
        self, api_client, national_admin, national_staff
    ):
        """Explicit grant overrides default denial."""
        api_client.force_authenticate(user=national_admin)
        
        # Get initial permissions
        initial_response = api_client.get(
            f'/api/admin/users/{national_staff.id}/permissions/'
        )
        initial_has_perm = initial_response.data['permissions'].get(
            'manage_cache', {}
        ).get('has_permission', False)
        
        # Grant a permission that staff don't have by default
        api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {'permission': 'manage_cache'},
            format='json'
        )
        
        # Check it's now granted
        response = api_client.get(
            f'/api/admin/users/{national_staff.id}/permissions/'
        )
        
        perm_status = response.data['permissions']['manage_cache']
        assert perm_status['has_permission'] is True
        assert perm_status['source'] == 'granted'
    
    def test_explicit_revoke_overrides_default(
        self, api_client, national_admin, national_staff
    ):
        """Explicit revoke overrides default grant."""
        api_client.force_authenticate(user=national_admin)
        
        # Revoke a permission that staff have by default
        api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/revoke/',
            {'permission': 'view_users'},  # Staff have this by default
            format='json'
        )
        
        # Check it's now revoked
        response = api_client.get(
            f'/api/admin/users/{national_staff.id}/permissions/'
        )
        
        perm_status = response.data['permissions']['view_users']
        assert perm_status['has_permission'] is False
        assert perm_status['source'] == 'revoked'


@pytest.mark.django_db
class TestJurisdictionScoping:
    """Test that jurisdiction scoping is enforced."""
    
    def test_regional_admin_cannot_manage_other_region(
        self, api_client, regional_admin, regional_staff_ashanti
    ):
        """Regional admin cannot grant permissions to users in other regions."""
        api_client.force_authenticate(user=regional_admin)
        
        response = api_client.post(
            f'/api/admin/users/{regional_staff_ashanti.id}/permissions/grant/',
            {'permission': 'view_farms'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_constituency_admin_scope(
        self, api_client, constituency_admin, constituency_staff, extension_officer
    ):
        """Constituency admin can manage users in their constituency."""
        api_client.force_authenticate(user=constituency_admin)
        
        # Can manage constituency staff
        response1 = api_client.post(
            f'/api/admin/users/{constituency_staff.id}/permissions/grant/',
            {'permission': 'view_applications'},
            format='json'
        )
        assert response1.status_code == status.HTTP_200_OK
        
        # Can manage extension officer in their constituency
        response2 = api_client.post(
            f'/api/admin/users/{extension_officer.id}/permissions/grant/',
            {'permission': 'view_applications'},
            format='json'
        )
        assert response2.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAuthenticationAndAuthorization:
    """Test authentication and authorization requirements."""
    
    def test_unauthenticated_access_denied(self, api_client):
        """Unauthenticated users cannot access permission endpoints."""
        response = api_client.get('/api/admin/permissions/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_farmer_cannot_access_admin_endpoints(self, api_client, farmer):
        """Farmers cannot access admin permission endpoints."""
        api_client.force_authenticate(user=farmer)
        
        endpoints = [
            '/api/admin/permissions/',
            '/api/admin/permissions/manageable-users/',
        ]
        
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_staff_cannot_manage_permissions(
        self, api_client, national_staff, regional_staff
    ):
        """Staff roles cannot manage permissions."""
        api_client.force_authenticate(user=national_staff)
        
        response = api_client.post(
            f'/api/admin/users/{regional_staff.id}/permissions/grant/',
            {'permission': 'view_farms'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_user_not_found(self, api_client, national_admin):
        """Returns 404 for non-existent user."""
        api_client.force_authenticate(user=national_admin)
        
        fake_id = '00000000-0000-0000-0000-000000000000'
        response = api_client.get(f'/api/admin/users/{fake_id}/permissions/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['code'] == 'USER_NOT_FOUND'
    
    def test_missing_permission_codename(self, api_client, national_admin, national_staff):
        """Returns 400 when permission codename is missing."""
        api_client.force_authenticate(user=national_admin)
        
        response = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {},  # Missing 'permission' key
            format='json'
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'MISSING_PERMISSION' in response.data['code']
    
    def test_grant_same_permission_twice(
        self, api_client, national_admin, national_staff
    ):
        """Granting same permission twice is idempotent."""
        api_client.force_authenticate(user=national_admin)
        
        # Grant once
        response1 = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {'permission': 'create_batches'},
            format='json'
        )
        assert response1.status_code == status.HTTP_200_OK
        
        # Grant again
        response2 = api_client.post(
            f'/api/admin/users/{national_staff.id}/permissions/grant/',
            {'permission': 'create_batches'},
            format='json'
        )
        assert response2.status_code == status.HTTP_200_OK
        
        # Should only have one record
        assert UserPermission.objects.filter(
            user=national_staff,
            permission__codename='create_batches'
        ).count() == 1


@pytest.mark.django_db
class TestLegacyRoleCompatibility:
    """Test that legacy role names work correctly."""
    
    def test_regional_coordinator_works_as_regional_admin(self, api_client, db):
        """REGIONAL_COORDINATOR works as alias for REGIONAL_ADMIN."""
        coordinator = User.objects.create_user(
            username='coordinator',
            email='coordinator@test.com',
            password='testpass123',
            role='REGIONAL_COORDINATOR',  # Legacy role name
            region='Greater Accra',
            phone='+233240000020',
        )
        
        regional_staff = User.objects.create_user(
            username='regional_staff_for_coord',
            email='staff@test.com',
            password='testpass123',
            role='REGIONAL_STAFF',
            region='Greater Accra',
            phone='+233240000021',
        )
        
        api_client.force_authenticate(user=coordinator)
        
        # Should be able to manage regional staff
        response = api_client.post(
            f'/api/admin/users/{regional_staff.id}/permissions/grant/',
            {'permission': 'view_farms'},
            format='json'
        )
        
        assert response.status_code == status.HTTP_200_OK


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
