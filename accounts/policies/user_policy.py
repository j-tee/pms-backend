"""
User Management Authorization Policy

Defines access control rules for user management.

Role Hierarchy for User Management:
    SUPER_ADMIN - Can manage all users (except other SUPER_ADMINs)
    NATIONAL_ADMIN - Can manage all users except SUPER_ADMIN, can manage NATIONAL_STAFF permissions
    NATIONAL_STAFF - Limited access, permissions managed by NATIONAL_ADMIN
    REGIONAL_ADMIN - Can manage users in their region, can manage REGIONAL_STAFF permissions
    REGIONAL_STAFF - Limited regional access, permissions managed by REGIONAL_ADMIN
    CONSTITUENCY_ADMIN - Can manage users in their constituency, can manage CONSTITUENCY_STAFF permissions
    CONSTITUENCY_STAFF - Limited constituency access, permissions managed by CONSTITUENCY_ADMIN
    Field Officers - Can view assigned farmers only
    FARMER - Can view own profile only
"""

from .base_policy import BasePolicy


class UserPolicy(BasePolicy):
    """Authorization policy for User model."""
    
    @classmethod
    def can_view(cls, user, target_user):
        """
        Check if user can view target user's profile.
        
        Access Rules:
        - Super Admin: All users
        - National Admin/Staff: All users (staff requires permission)
        - Regional Admin/Staff: Users in their region
        - Constituency Admin/Staff: Users in their constituency
        - Field Officers: Assigned farmers
        - Users: Own profile
        """
        # Can view own profile
        if user == target_user:
            return True
        
        # Admins can view all
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        # National staff with permission
        if cls.is_national_staff(user) and cls.has_permission(user, 'view_all_users'):
            return True
        
        # Regional admin/staff can view users in region
        if cls.is_regional_admin(user):
            if target_user.region == user.region:
                return True
        
        if cls.is_regional_staff(user) and cls.has_permission(user, 'view_regional_users'):
            if target_user.region == user.region:
                return True
        
        # Constituency admin/staff can view users in constituency
        if cls.is_constituency_admin(user):
            if target_user.constituency == user.constituency:
                return True
        
        if cls.is_constituency_staff(user) and cls.has_permission(user, 'view_constituency_users'):
            if target_user.constituency == user.constituency:
                return True
        
        # Field officers (extension, vet, YEA official) can view their assigned farmers
        if cls.is_field_officer(user):
            from farms.models import Farm
            # Check if target is a farmer assigned to this field officer
            return Farm.objects.filter(
                owner=target_user,
                extension_officer=user
            ).exists()
        
        return False
    
    @classmethod
    def can_create(cls, user):
        """
        Check if user can create new users.
        
        Access Rules:
        - Super Admin: Can create any user type
        - National Admin: Can create any user type (except SUPER_ADMIN)
        - Regional Admin: Can create constituency-level users and field officers in region
        - Constituency Admin: Can create field officers in constituency
        """
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_regional_admin(user):
            return True  # Limited to certain roles (checked in can_create_role)
        
        if cls.is_constituency_admin(user):
            return True  # Limited to field officers (checked in can_create_role)
        
        return False
    
    @classmethod
    def can_create_role(cls, user, target_role):
        """
        Check if user can create user with specific role.
        
        Args:
            user: User attempting to create
            target_role: Role to be assigned to new user
        """
        if cls.is_super_admin(user):
            return True  # Can create any role except other SUPER_ADMIN
        
        if cls.is_national_admin(user):
            # Cannot create super admin
            return target_role != 'SUPER_ADMIN'
        
        if cls.is_regional_admin(user):
            # Can create constituency-level users and field officers
            return target_role in [
                'CONSTITUENCY_ADMIN', 'CONSTITUENCY_OFFICIAL',  # Legacy support
                'CONSTITUENCY_STAFF',
                'EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL'
            ]
        
        if cls.is_constituency_admin(user):
            # Can only create field officers
            return target_role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL']
        
        return False
    
    @classmethod
    def can_edit(cls, user, target_user):
        """
        Check if user can edit target user.
        
        Access Rules:
        - SUPER_ADMIN accounts can ONLY be edited by themselves (protected accounts)
        - Super Admin: All other users
        - National Admin: All except super admin
        - Regional Admin: Users in their region (limited roles)
        - Constituency Admin: Users in their constituency (limited roles)
        - Users: Own profile (limited fields)
        
        SECURITY: SUPER_ADMIN accounts are fully protected and cannot be modified
        by any other user, including other SUPER_ADMINs.
        """
        # Can edit own profile
        if user == target_user:
            return True
        
        # SECURITY: SUPER_ADMIN accounts cannot be edited by anyone else
        if cls.is_super_admin(target_user):
            return False  # Only self-edit allowed (handled above)
        
        # Super admin can edit all non-SUPER_ADMIN users
        if cls.is_super_admin(user):
            return True
        
        # National admin can edit all except super admin
        if cls.is_national_admin(user):
            return not cls.is_super_admin(target_user)
        
        # Regional admin can edit users in region
        if cls.is_regional_admin(user):
            if target_user.region == user.region:
                # Can edit constituency-level users and field officers
                return target_user.role in [
                    'CONSTITUENCY_ADMIN', 'CONSTITUENCY_OFFICIAL',
                    'CONSTITUENCY_STAFF',
                    'EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL'
                ]
        
        # Constituency admin can edit users in constituency
        if cls.is_constituency_admin(user):
            if target_user.constituency == user.constituency:
                # Can only edit field officers
                return target_user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL']
        
        return False
    
    @classmethod
    def can_delete(cls, user, target_user):
        """
        Check if user can delete target user.
        
        Access Rules:
        - SUPER_ADMIN accounts CANNOT be deleted (protected accounts)
        - Only super admin can delete other users
        - Cannot delete self
        
        SECURITY: SUPER_ADMIN accounts are fully protected and cannot be deleted
        by anyone, including themselves or other SUPER_ADMINs.
        """
        if user == target_user:
            return False  # Cannot delete self
        
        # SECURITY: SUPER_ADMIN accounts cannot be deleted by anyone
        if cls.is_super_admin(target_user):
            return False
        
        return cls.is_super_admin(user)
    
    @classmethod
    def can_suspend(cls, user, target_user):
        """
        Check if user can suspend target user.
        
        Access Rules:
        - SUPER_ADMIN accounts CANNOT be suspended (protected accounts)
        - Super Admin: All non-SUPER_ADMIN users
        - National Admin: All except super admin and self
        
        SECURITY: SUPER_ADMIN accounts are fully protected and cannot be suspended
        by anyone, including other SUPER_ADMINs.
        """
        if user == target_user:
            return False  # Cannot suspend self
        
        # SECURITY: SUPER_ADMIN accounts cannot be suspended by anyone
        if cls.is_super_admin(target_user):
            return False
        
        if cls.is_super_admin(user):
            return True
        
        if cls.is_national_admin(user):
            return True
        
        return False
    
    @classmethod
    def can_assign_role(cls, user, target_user, role_name):
        """
        Check if user can assign role to target user.
        
        Access Rules:
        - SUPER_ADMIN accounts cannot have their role changed (protected accounts)
        - Super Admin: Can assign any role to non-SUPER_ADMIN users
        - National Admin: Can assign most roles (not SUPER_ADMIN)
        - Regional Admin: Limited roles in region
        - Constituency Admin: Limited roles in constituency
        
        SECURITY: SUPER_ADMIN accounts are fully protected. Their role cannot
        be changed by anyone.
        """
        # SECURITY: Cannot change role of SUPER_ADMIN accounts
        if cls.is_super_admin(target_user):
            return False
        
        if cls.is_super_admin(user):
            # Cannot create new SUPER_ADMIN via role assignment
            return role_name != 'SUPER_ADMIN'
        
        if cls.is_national_admin(user):
            # Cannot assign super admin role
            return role_name != 'SUPER_ADMIN'
        
        if cls.is_regional_admin(user):
            # Can only assign certain roles in their region
            if target_user.region != user.region:
                return False
            return role_name in [
                'CONSTITUENCY_ADMIN', 'CONSTITUENCY_OFFICIAL',
                'CONSTITUENCY_STAFF',
                'EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL'
            ]
        
        if cls.is_constituency_admin(user):
            # Can only assign field officer roles in their constituency
            if target_user.constituency != user.constituency:
                return False
            return role_name in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL']
        
        return False
    
    @classmethod
    def can_reset_password(cls, user, target_user):
        """
        Check if user can reset target user's password.
        
        Access Rules:
        - SUPER_ADMIN: Can only reset their own password (except for self-service)
        - Super Admin: All non-SUPER_ADMIN users
        - National Admin: All except super admin
        - Users: Can request own password reset
        
        SECURITY: Other users cannot trigger password resets for SUPER_ADMIN accounts.
        """
        if user == target_user:
            return True  # Can reset own
        
        # SECURITY: Cannot reset password of SUPER_ADMIN accounts
        if cls.is_super_admin(target_user):
            return False
        
        if cls.is_super_admin(user):
            return True
        
        if cls.is_national_admin(user):
            return True
        
        return False
    
    @classmethod
    def can_impersonate(cls, user, target_user):
        """
        Check if user can impersonate target user.
        
        Access Rules:
        - Only super admin
        - Cannot impersonate other super admins
        """
        if not cls.is_super_admin(user):
            return False
        
        # Cannot impersonate other super admins
        return not cls.is_super_admin(target_user)
    
    @classmethod
    def editable_fields(cls, user, target_user):
        """
        Get list of fields user can edit on target user.
        """
        if user == target_user:
            # Users can edit own profile fields
            return [
                'first_name', 'last_name', 'email', 'phone',
                'preferred_contact_method'
            ]
        
        if cls.is_super_admin(user):
            return '__all__'
        
        if cls.is_national_admin(user):
            # Cannot edit certain system fields
            return [
                'first_name', 'last_name', 'email', 'phone',
                'role', 'region', 'constituency', 'is_active',
                'is_verified'
            ]
        
        if cls.is_regional_admin(user):
            return [
                'first_name', 'last_name', 'email', 'phone',
                'constituency', 'is_active'
            ]
        
        if cls.is_constituency_admin(user):
            return [
                'first_name', 'last_name', 'email', 'phone',
                'is_active'
            ]
        
        return []
    
    @classmethod
    def can_view_users(cls, user):
        """Check if user can view user list."""
        return cls.has_admin_access(user) or cls.is_field_officer(user)
    
    @classmethod
    def scope(cls, user, queryset=None):
        """Filter users based on access level."""
        if queryset is None:
            from accounts.models import User
            queryset = User.objects.all()
        
        # Super admin and national level see all
        if cls.is_super_admin(user) or cls.is_national_level(user):
            return queryset
        
        # Regional admin/staff sees users in region
        if cls.is_regional_level(user):
            return queryset.filter(region=user.region)
        
        # Constituency admin/staff sees users in constituency
        if cls.is_constituency_level(user):
            return queryset.filter(constituency=user.constituency)
        
        # Field officers (extension, vet, YEA official) see assigned farmers
        if cls.is_field_officer(user):
            from farms.models import Farm
            farmer_ids = Farm.objects.filter(
                extension_officer=user
            ).values_list('owner_id', flat=True)
            return queryset.filter(id__in=farmer_ids)
        
        # Default: see only self
        return queryset.filter(id=user.id)
    
    # ========================================
    # PERMISSION MANAGEMENT
    # ========================================
    
    @classmethod
    def can_manage_permissions(cls, user, target_user):
        """
        Check if user can manage target user's permissions.
        
        Access Rules:
        - Super Admin: All users (except other SUPER_ADMINs)
        - National Admin: NATIONAL_STAFF, and all below
        - Regional Admin: REGIONAL_STAFF, and constituency/field level in their region
        - Constituency Admin: CONSTITUENCY_STAFF and field officers in their constituency
        """
        # Cannot manage own permissions
        if user == target_user:
            return False
        
        # Cannot manage SUPER_ADMIN
        if cls.is_super_admin(target_user):
            return False
        
        # Super admin can manage all (except other super admins)
        if cls.is_super_admin(user):
            return True
        
        # National admin can manage national staff and below
        if cls.is_national_admin(user):
            return target_user.role not in ['SUPER_ADMIN']
        
        # Regional admin can manage regional staff and below in their region
        if cls.is_regional_admin(user):
            if target_user.region != user.region:
                return False
            return target_user.role in [
                'REGIONAL_STAFF',
                'CONSTITUENCY_ADMIN', 'CONSTITUENCY_OFFICIAL',
                'CONSTITUENCY_STAFF',
                'EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL'
            ]
        
        # Constituency admin can manage constituency staff and field officers
        if cls.is_constituency_admin(user):
            if target_user.constituency != user.constituency:
                return False
            return target_user.role in [
                'CONSTITUENCY_STAFF',
                'EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL'
            ]
        
        return False
    
    @classmethod
    def can_grant_permission(cls, user, target_user, permission_codename):
        """
        Check if user can grant a specific permission to target user.
        
        Uses the permission management service for detailed checks.
        """
        if not cls.can_manage_permissions(user, target_user):
            return False
        
        # Check if this admin can grant this specific permission
        from accounts.permissions_config import GRANTABLE_PERMISSIONS
        
        grantable = GRANTABLE_PERMISSIONS.get(user.role, [])
        return permission_codename in grantable
