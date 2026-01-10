"""
Permission Management Service

Provides services for managing user permissions at each level.
Admins can grant/revoke permissions for staff within their jurisdiction.
"""

from django.db import transaction
from accounts.models import User
from accounts.roles import Permission, UserPermission
from accounts.permissions_config import (
    SYSTEM_PERMISSIONS,
    PERMISSION_CATEGORIES,
    PERMISSION_MANAGEMENT_HIERARCHY,
    GRANTABLE_PERMISSIONS,
    can_admin_manage_role,
    can_admin_grant_permission,
    get_implicit_permissions,
    get_default_permissions,
    get_permission_by_codename,
)


class PermissionManagementError(Exception):
    """Exception raised for permission management errors."""
    pass


class PermissionManagementService:
    """
    Service for managing user permissions.
    
    Usage:
        service = PermissionManagementService(admin_user)
        service.grant_permission(target_user, 'can_approve_applications', reason='Temporary coverage')
        service.revoke_permission(target_user, 'can_export_reports')
        service.get_manageable_permissions(target_user)
    """
    
    def __init__(self, admin_user):
        """
        Initialize the service with the admin performing the action.
        
        Args:
            admin_user: User instance with admin privileges
        """
        self.admin = admin_user
        self._validate_admin()
    
    def _validate_admin(self):
        """Validate that the user has permission management capabilities."""
        manageable = PERMISSION_MANAGEMENT_HIERARCHY.get(self.admin.role, [])
        if not manageable and self.admin.role != 'SUPER_ADMIN':
            raise PermissionManagementError(
                f"Role '{self.admin.role}' cannot manage permissions for any users"
            )
    
    def can_manage_user(self, target_user):
        """
        Check if admin can manage permissions for target user.
        
        Args:
            target_user: User whose permissions may be managed
            
        Returns:
            bool: True if admin can manage this user's permissions
        """
        if self.admin.role == 'SUPER_ADMIN':
            return target_user.role != 'SUPER_ADMIN' or self.admin.id == target_user.id
        
        if not can_admin_manage_role(self.admin.role, target_user.role):
            return False
        
        # Check jurisdiction
        if self.admin.role == 'NATIONAL_ADMIN':
            return True  # National admin can manage nationally
        
        if self.admin.role == 'REGIONAL_ADMIN':
            # Can only manage users in their region
            return target_user.region == self.admin.region
        
        if self.admin.role == 'CONSTITUENCY_ADMIN':
            # Can only manage users in their constituency
            return target_user.constituency == self.admin.constituency
        
        return False
    
    def get_manageable_users(self, queryset=None):
        """
        Get users that this admin can manage permissions for.
        
        Args:
            queryset: Optional base queryset to filter
            
        Returns:
            QuerySet of User instances
        """
        if queryset is None:
            queryset = User.objects.filter(is_active=True)
        
        manageable_roles = PERMISSION_MANAGEMENT_HIERARCHY.get(self.admin.role, [])
        
        if self.admin.role == 'SUPER_ADMIN':
            # Can manage all except other super admins (but can see themselves)
            return queryset.exclude(role='SUPER_ADMIN').union(
                queryset.filter(id=self.admin.id)
            )
        
        queryset = queryset.filter(role__in=manageable_roles)
        
        # Apply jurisdiction filter
        if self.admin.role == 'REGIONAL_ADMIN':
            queryset = queryset.filter(region=self.admin.region)
        elif self.admin.role == 'CONSTITUENCY_ADMIN':
            queryset = queryset.filter(constituency=self.admin.constituency)
        
        return queryset
    
    def get_grantable_permissions(self):
        """
        Get permissions that this admin can grant to users.
        
        Returns:
            List of permission info dicts
        """
        if self.admin.role == 'SUPER_ADMIN':
            # Can grant all permissions
            return [
                {
                    'codename': perm[0],
                    'name': perm[1],
                    'description': perm[2],
                    'category': perm[3],
                }
                for perm in SYSTEM_PERMISSIONS
            ]
        
        grantable_codenames = GRANTABLE_PERMISSIONS.get(self.admin.role, [])
        return [
            {
                'codename': perm[0],
                'name': perm[1],
                'description': perm[2],
                'category': perm[3],
            }
            for perm in SYSTEM_PERMISSIONS
            if perm[0] in grantable_codenames
        ]
    
    def get_user_permissions(self, target_user):
        """
        Get detailed permission status for a user.
        
        Returns dict where keys are permission codenames and values contain:
        - name: Permission name
        - description: Permission description
        - category: Permission category
        - source: How user got this permission (implicit/default/granted)
        - active: Whether permission is currently active
        - can_revoke: Whether this permission can be revoked
        - granted_by: Who granted (if explicitly granted)
        - granted_at: When granted (if explicitly granted)
        - reason: Why granted/revoked
        """
        if not self.can_manage_user(target_user):
            raise PermissionManagementError(
                f"You cannot manage permissions for user '{target_user.username}'"
            )
        
        from accounts.permissions_config import get_permissions_as_dict
        
        # Get all permissions as dict
        all_permissions = get_permissions_as_dict()
        
        # Get implicit permissions (admin roles)
        implicit = get_implicit_permissions(target_user.role)
        if implicit == '__all__':
            from accounts.permissions_config import get_all_permission_codenames
            implicit = get_all_permission_codenames()
        implicit_set = set(implicit or [])
        
        # Get default permissions (staff roles)
        defaults_set = set(get_default_permissions(target_user.role) or [])
        
        # Get explicit grants/revokes
        explicit_grants = {
            p['permission__codename']: p
            for p in UserPermission.objects.filter(user=target_user, is_granted=True)
            .select_related('permission', 'granted_by')
            .values('permission__codename', 'granted_by__username', 'granted_at', 'reason')
        }
        
        explicit_revokes = {
            p['permission__codename']: p
            for p in UserPermission.objects.filter(user=target_user, is_granted=False)
            .select_related('permission', 'granted_by')
            .values('permission__codename', 'granted_by__username', 'granted_at', 'reason')
        }
        
        # Build permission details dict
        permissions = {}
        for codename, details in all_permissions.items():
            # Determine source and active status
            if codename in implicit_set:
                source = 'implicit'
                active = codename not in explicit_revokes  # Implicit can't be revoked, but track attempts
                can_revoke = False
            elif codename in explicit_revokes:
                source = 'revoked'
                active = False
                can_revoke = True
            elif codename in explicit_grants:
                source = 'granted'
                active = True
                can_revoke = True
            elif codename in defaults_set:
                source = 'default'
                active = True
                can_revoke = True
            else:
                source = 'none'
                active = False
                can_revoke = False
            
            permission_info = {
                'name': details['name'],
                'description': details['description'],
                'category': details['category'],
                'source': source,
                'active': active,
                'can_revoke': can_revoke,
            }
            
            # Add grant/revoke metadata if applicable
            if codename in explicit_grants:
                grant_info = explicit_grants[codename]
                permission_info.update({
                    'granted_by': grant_info['granted_by__username'],
                    'granted_at': grant_info['granted_at'].isoformat() if grant_info['granted_at'] else None,
                    'reason': grant_info.get('reason', ''),
                })
            elif codename in explicit_revokes:
                revoke_info = explicit_revokes[codename]
                permission_info.update({
                    'revoked_by': revoke_info['granted_by__username'],
                    'revoked_at': revoke_info['granted_at'].isoformat() if revoke_info['granted_at'] else None,
                    'reason': revoke_info.get('reason', ''),
                })
            
            permissions[codename] = permission_info
        
        return permissions
    
    @transaction.atomic
    def grant_permission(self, target_user, permission_codename, reason=''):
        """
        Grant a permission to a user.
        
        Args:
            target_user: User to grant permission to
            permission_codename: Codename of permission to grant
            reason: Optional reason for granting
            
        Returns:
            dict with result info
        """
        # Validate management rights
        if not self.can_manage_user(target_user):
            raise PermissionManagementError(
                f"You cannot manage permissions for user '{target_user.username}'"
            )
        
        # Validate permission exists
        perm_info = get_permission_by_codename(permission_codename)
        if not perm_info:
            raise PermissionManagementError(
                f"Permission '{permission_codename}' does not exist"
            )
        
        # Validate admin can grant this permission
        if not can_admin_grant_permission(self.admin.role, permission_codename):
            raise PermissionManagementError(
                f"You cannot grant permission '{permission_codename}'"
            )
        
        # Check if it's an implicit permission (cannot be modified)
        implicit = get_implicit_permissions(target_user.role)
        if implicit and (implicit == '__all__' or permission_codename in implicit):
            raise PermissionManagementError(
                f"Permission '{permission_codename}' is implicit for role '{target_user.role}' and cannot be modified"
            )
        
        # Ensure permission exists in database
        permission, _ = Permission.objects.get_or_create(
            codename=permission_codename,
            defaults={
                'name': perm_info['name'],
                'description': perm_info['description'],
                'category': perm_info['category'],
                'is_system_permission': True,
            }
        )
        
        # Grant the permission
        user_perm = target_user.grant_permission(
            permission_codename,
            granted_by=self.admin,
            reason=reason
        )
        
        return {
            'success': True,
            'action': 'granted',
            'permission': permission_codename,
            'user': target_user.username,
            'granted_by': self.admin.username,
        }
    
    @transaction.atomic
    def revoke_permission(self, target_user, permission_codename, reason=''):
        """
        Revoke a permission from a user.
        
        Args:
            target_user: User to revoke permission from
            permission_codename: Codename of permission to revoke
            reason: Optional reason for revoking
            
        Returns:
            dict with result info
        """
        # Validate management rights
        if not self.can_manage_user(target_user):
            raise PermissionManagementError(
                f"You cannot manage permissions for user '{target_user.username}'"
            )
        
        # Validate permission exists
        perm_info = get_permission_by_codename(permission_codename)
        if not perm_info:
            raise PermissionManagementError(
                f"Permission '{permission_codename}' does not exist"
            )
        
        # Check if it's an implicit permission (cannot be revoked)
        implicit = get_implicit_permissions(target_user.role)
        if implicit and (implicit == '__all__' or permission_codename in implicit):
            raise PermissionManagementError(
                f"Permission '{permission_codename}' is implicit for role '{target_user.role}' and cannot be revoked"
            )
        
        # Revoke the permission
        target_user.revoke_permission(
            permission_codename,
            revoked_by=self.admin,
            reason=reason
        )
        
        return {
            'success': True,
            'action': 'revoked',
            'permission': permission_codename,
            'user': target_user.username,
            'revoked_by': self.admin.username,
        }
    
    @transaction.atomic
    def reset_permission(self, target_user, permission_codename):
        """
        Reset a permission to its default state for the user's role.
        
        This removes any explicit grant or revoke.
        
        Args:
            target_user: User to reset permission for
            permission_codename: Codename of permission to reset
            
        Returns:
            dict with result info
        """
        if not self.can_manage_user(target_user):
            raise PermissionManagementError(
                f"You cannot manage permissions for user '{target_user.username}'"
            )
        
        cleared = target_user.clear_permission_override(permission_codename)
        
        return {
            'success': True,
            'action': 'reset',
            'permission': permission_codename,
            'user': target_user.username,
            'had_override': cleared,
        }
    
    @transaction.atomic
    def bulk_update_permissions(self, target_user, grants=None, revokes=None, reason=''):
        """
        Update multiple permissions at once.
        
        Args:
            target_user: User to update permissions for
            grants: List of permission codenames to grant
            revokes: List of permission codenames to revoke
            reason: Optional reason for the changes
            
        Returns:
            dict with results
        """
        grants = grants or []
        revokes = revokes or []
        
        results = {
            'granted': [],
            'revoked': [],
            'errors': [],
        }
        
        for codename in grants:
            try:
                self.grant_permission(target_user, codename, reason)
                results['granted'].append(codename)
            except PermissionManagementError as e:
                results['errors'].append({'codename': codename, 'error': str(e)})
        
        for codename in revokes:
            try:
                self.revoke_permission(target_user, codename, reason)
                results['revoked'].append(codename)
            except PermissionManagementError as e:
                results['errors'].append({'codename': codename, 'error': str(e)})
        
        return results


def sync_permissions_to_database():
    """
    Sync all system permissions from permissions_config to the database.
    
    This should be called during deployment/migration to ensure
    all permissions exist in the database.
    """
    from accounts.roles import Permission
    
    created_count = 0
    updated_count = 0
    
    for perm_tuple in SYSTEM_PERMISSIONS:
        codename, name, description, category, _ = perm_tuple
        
        permission, created = Permission.objects.update_or_create(
            codename=codename,
            defaults={
                'name': name,
                'description': description,
                'category': category,
                'is_system_permission': True,
            }
        )
        
        if created:
            created_count += 1
        else:
            updated_count += 1
    
    return {
        'created': created_count,
        'updated': updated_count,
        'total': len(SYSTEM_PERMISSIONS),
        'synced': created_count + updated_count,
    }
