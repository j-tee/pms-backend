"""
User Management Authorization Policy

Defines access control rules for user management.
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
        - National Admin: All users
        - Regional Coordinator: Users in their region
        - Constituency Official: Users in their constituency
        - Users: Own profile
        """
        # Can view own profile
        if user == target_user:
            return True
        
        # Admins can view all
        if cls.is_super_admin(user) or cls.is_yea_official(user) or cls.is_national_admin(user):
            return True
        
        # Regional coordinator can view users in region
        if cls.is_regional_coordinator(user):
            if target_user.region == user.region:
                return True
        
        # Constituency official can view users in constituency
        if cls.is_constituency_official(user):
            if target_user.constituency == user.constituency:
                return True
        
        # Extension officer can view their assigned farmers
        if cls.is_extension_officer(user):
            from farms.models import Farm
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
        - National Admin: Can create any user type
        - Regional Coordinator: Can create constituency officials and extension officers in region
        """
        if cls.is_super_admin(user) or cls.is_yea_official(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_regional_coordinator(user):
            return True  # Limited to certain roles
        
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
        
        if cls.is_yea_official(user) or cls.is_national_admin(user):
            # Cannot create super admin or YEA official
            return target_role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']
        
        if cls.is_regional_coordinator(user):
            # Can only create constituency officials and extension officers
            return target_role in ['CONSTITUENCY_OFFICIAL', 'EXTENSION_OFFICER']
        
        return False
    
    @classmethod
    def can_edit(cls, user, target_user):
        """
        Check if user can edit target user.
        
        Access Rules:
        - Super Admin: All users
        - National Admin: All except super admin
        - Regional Coordinator: Users in their region (limited roles)
        - Users: Own profile (limited fields)
        """
        # Can edit own profile
        if user == target_user:
            return True
        
        # Super admin can edit all
        if cls.is_super_admin(user):
            return True
        
        # YEA Official can edit all except super admin and other YEA officials
        if cls.is_yea_official(user):
            return not (cls.is_super_admin(target_user) or cls.is_yea_official(target_user))
        
        # National admin can edit all except super admin and YEA officials
        if cls.is_national_admin(user):
            return not (cls.is_super_admin(target_user) or cls.is_yea_official(target_user))
        
        # Regional coordinator can edit users in region
        if cls.is_regional_coordinator(user):
            if target_user.region == user.region:
                # Can only edit constituency officials and extension officers
                return target_user.role in ['CONSTITUENCY_OFFICIAL', 'EXTENSION_OFFICER']
        
        return False
    
    @classmethod
    def can_delete(cls, user, target_user):
        """
        Check if user can delete target user.
        
        Access Rules:
        - Only super admin
        - Cannot delete self
        """
        if user == target_user:
            return False  # Cannot delete self
        
        return cls.is_super_admin(user)
    
    @classmethod
    def can_suspend(cls, user, target_user):
        """
        Check if user can suspend target user.
        
        Access Rules:
        - Super Admin: All users
        - National Admin: All except super admin and self
        """
        if user == target_user:
            return False  # Cannot suspend self
        
        if cls.is_super_admin(user):
            return True
        
        if cls.is_yea_official(user):
            return not (cls.is_super_admin(target_user) or cls.is_yea_official(target_user))
        
        if cls.is_national_admin(user):
            return not (cls.is_super_admin(target_user) or cls.is_yea_official(target_user))
        
        return False
    
    @classmethod
    def can_assign_role(cls, user, target_user, role_name):
        """
        Check if user can assign role to target user.
        
        Access Rules:
        - Super Admin: Can assign any role
        - National Admin: Can assign most roles
        - Regional Coordinator: Limited roles in region
        """
        if cls.is_super_admin(user):
            return True
        
        if cls.is_yea_official(user) or cls.is_national_admin(user):
            # Cannot assign super admin or YEA official roles
            return role_name not in ['SUPER_ADMIN', 'YEA_OFFICIAL']
        
        if cls.is_regional_coordinator(user):
            # Can only assign certain roles in their region
            if target_user.region != user.region:
                return False
            return role_name in ['CONSTITUENCY_OFFICIAL', 'EXTENSION_OFFICER']
        
        return False
    
    @classmethod
    def can_reset_password(cls, user, target_user):
        """
        Check if user can reset target user's password.
        
        Access Rules:
        - Super Admin: All users
        - National Admin: All except super admin
        - Users: Can request own password reset
        """
        if user == target_user:
            return True  # Can reset own
        
        if cls.is_super_admin(user):
            return True
        
        if cls.is_yea_official(user):
            return not (cls.is_super_admin(target_user) or cls.is_yea_official(target_user))
        
        if cls.is_national_admin(user):
            return not (cls.is_super_admin(target_user) or cls.is_yea_official(target_user))
        
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
        
        if cls.is_regional_coordinator(user):
            return [
                'first_name', 'last_name', 'email', 'phone',
                'constituency', 'is_active'
            ]
        
        return []
    
    @classmethod
    def can_view_users(cls, user):
        """Check if user can view user list."""
        return cls.has_admin_access(user) or cls.is_extension_officer(user)
    
    @classmethod
    def scope(cls, user, queryset=None):
        """Filter users based on access level."""
        if queryset is None:
            from accounts.models import User
            queryset = User.objects.all()
        
        # Admins see all
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return queryset
        
        # Regional coordinator sees users in region
        if cls.is_regional_coordinator(user):
            return queryset.filter(region=user.region)
        
        # Constituency official sees users in constituency
        if cls.is_constituency_official(user):
            return queryset.filter(constituency=user.constituency)
        
        # Extension officer sees assigned farmers
        if cls.is_extension_officer(user):
            from farms.models import Farm
            farmer_ids = Farm.objects.filter(
                extension_officer=user
            ).values_list('owner_id', flat=True)
            return queryset.filter(id__in=farmer_ids)
        
        # Default: see only self
        return queryset.filter(id=user.id)
