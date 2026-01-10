"""
Base Policy Class

Provides common authorization methods for all policy classes.

Role Hierarchy:
    SUPER_ADMIN (Platform Owner)
        ↓
    NATIONAL_ADMIN / NATIONAL_STAFF (National Level)
        ↓
    REGIONAL_ADMIN / REGIONAL_STAFF (Regional Level)
        ↓
    CONSTITUENCY_ADMIN / CONSTITUENCY_STAFF (Constituency Level)
        ↓
    Field Officers: EXTENSION_OFFICER, VETERINARY_OFFICER, YEA_OFFICIAL
        ↓
    FARMER (End User)

Note: *_ADMIN roles have implicit permissions and can manage *_STAFF permissions.
      *_STAFF roles have configurable permissions managed by their admin.
"""


class BasePolicy:
    """
    Base class for all authorization policies.
    Provides helper methods for common permission checks.
    """
    
    # ========================================
    # PLATFORM LEVEL
    # ========================================
    
    @staticmethod
    def is_super_admin(user):
        """Check if user is super admin (platform owner - highest privilege)."""
        return user.role == 'SUPER_ADMIN'
    
    # ========================================
    # NATIONAL LEVEL
    # ========================================
    
    @staticmethod
    def is_national_admin(user):
        """Check if user is national admin (highest YEA staff role)."""
        return user.role == 'NATIONAL_ADMIN'
    
    @staticmethod
    def is_national_staff(user):
        """Check if user is national staff (permissions managed by national admin)."""
        return user.role == 'NATIONAL_STAFF'
    
    @staticmethod
    def is_national_level(user):
        """Check if user is at national level (admin or staff)."""
        return user.role in ['NATIONAL_ADMIN', 'NATIONAL_STAFF']
    
    # ========================================
    # REGIONAL LEVEL
    # ========================================
    
    @staticmethod
    def is_regional_admin(user):
        """Check if user is regional admin."""
        # Support both new and legacy role names
        return user.role in ['REGIONAL_ADMIN', 'REGIONAL_COORDINATOR']
    
    @staticmethod
    def is_regional_staff(user):
        """Check if user is regional staff (permissions managed by regional admin)."""
        return user.role == 'REGIONAL_STAFF'
    
    @staticmethod
    def is_regional_level(user):
        """Check if user is at regional level (admin or staff)."""
        return user.role in ['REGIONAL_ADMIN', 'REGIONAL_STAFF', 'REGIONAL_COORDINATOR']
    
    # Legacy alias
    @staticmethod
    def is_regional_coordinator(user):
        """Legacy: Check if user is regional coordinator. Use is_regional_admin instead."""
        return BasePolicy.is_regional_admin(user)
    
    # ========================================
    # CONSTITUENCY LEVEL
    # ========================================
    
    @staticmethod
    def is_constituency_admin(user):
        """Check if user is constituency admin."""
        # Support both new and legacy role names
        return user.role in ['CONSTITUENCY_ADMIN', 'CONSTITUENCY_OFFICIAL']
    
    @staticmethod
    def is_constituency_staff(user):
        """Check if user is constituency staff (permissions managed by constituency admin)."""
        return user.role == 'CONSTITUENCY_STAFF'
    
    @staticmethod
    def is_constituency_level(user):
        """Check if user is at constituency level (admin or staff)."""
        return user.role in ['CONSTITUENCY_ADMIN', 'CONSTITUENCY_STAFF', 'CONSTITUENCY_OFFICIAL']
    
    # Legacy alias
    @staticmethod
    def is_constituency_official(user):
        """Legacy: Check if user is constituency official. Use is_constituency_admin instead."""
        return BasePolicy.is_constituency_admin(user)
    
    # ========================================
    # FIELD OFFICER LEVEL
    # ========================================
    
    @staticmethod
    def is_extension_officer(user):
        """Check if user is extension officer."""
        return user.role == 'EXTENSION_OFFICER'
    
    @staticmethod
    def is_veterinary_officer(user):
        """Check if user is veterinary officer."""
        return user.role == 'VETERINARY_OFFICER'
    
    @staticmethod
    def is_yea_official(user):
        """Check if user is YEA field official."""
        return user.role == 'YEA_OFFICIAL'
    
    @staticmethod
    def is_field_officer(user):
        """Check if user is any type of field officer."""
        return user.role in ['EXTENSION_OFFICER', 'VETERINARY_OFFICER', 'YEA_OFFICIAL']
    
    # ========================================
    # SPECIALIZED ROLES
    # ========================================
    
    @staticmethod
    def is_procurement_officer(user):
        """Check if user is procurement officer."""
        return user.role == 'PROCUREMENT_OFFICER'
    
    @staticmethod
    def is_auditor(user):
        """Check if user is auditor."""
        return user.role == 'AUDITOR'
    
    @staticmethod
    def is_finance_officer(user):
        """Check if user is finance officer."""
        return user.role == 'FINANCE_OFFICER'
    
    # ========================================
    # END USER
    # ========================================
    
    @staticmethod
    def is_farmer(user):
        """Check if user is farmer."""
        return user.role == 'FARMER'
    
    @staticmethod
    def is_institutional_subscriber(user):
        """Check if user is institutional subscriber (B2B client)."""
        return user.role == 'INSTITUTIONAL_SUBSCRIBER'
    
    # ========================================
    # ACCESS LEVEL CHECKS
    # ========================================
    
    @staticmethod
    def is_admin_role(user):
        """Check if user has an admin role at any level."""
        return user.role in [
            'SUPER_ADMIN',
            'NATIONAL_ADMIN',
            'REGIONAL_ADMIN', 'REGIONAL_COORDINATOR',
            'CONSTITUENCY_ADMIN', 'CONSTITUENCY_OFFICIAL',
        ]
    
    @staticmethod
    def is_staff_role(user):
        """Check if user has a staff role (managed by an admin)."""
        return user.role in ['NATIONAL_STAFF', 'REGIONAL_STAFF', 'CONSTITUENCY_STAFF']
    
    @staticmethod
    def has_admin_access(user):
        """Check if user has any admin-level access (admin or staff with permissions)."""
        return (
            BasePolicy.is_admin_role(user) or
            BasePolicy.is_staff_role(user)
        )
    
    @staticmethod
    def has_elevated_admin_access(user):
        """Check if user has elevated admin access (Super Admin or National Admin)."""
        return user.role in ['SUPER_ADMIN', 'NATIONAL_ADMIN']
    
    @staticmethod
    def is_platform_staff(user):
        """
        Check if user is platform staff (Alphalogique employees).
        
        Platform staff have access to business-sensitive data that clients
        (YEA government, institutional subscribers) should not see.
        
        Examples of platform-only data:
        - Institutional subscription details (B2B contracts)
        - Platform revenue and financials
        - System-wide configuration
        
        Currently only SUPER_ADMIN is platform staff.
        """
        return user.role == 'SUPER_ADMIN'
    
    # ========================================
    # PERMISSION CHECKS
    # ========================================
    
    @staticmethod
    def has_permission(user, permission_codename):
        """
        Check if user has a specific permission.
        
        This uses the new permission system which considers:
        1. Implicit permissions from admin roles
        2. Default permissions for staff roles
        3. Explicitly granted/revoked permissions
        
        Args:
            user: User instance
            permission_codename: Codename of the permission to check
            
        Returns:
            bool: True if user has the permission
        """
        return user.has_permission(permission_codename)
    
    # ========================================
    # JURISDICTION CHECKS
    # ========================================
    
    @staticmethod
    def get_user_constituencies(user):
        """
        Get list of constituencies user has access to.
        
        Returns:
            List of constituency names
        """
        if BasePolicy.is_super_admin(user) or BasePolicy.is_national_level(user):
            # Access to all constituencies
            from farms.models import Farm
            return list(Farm.objects.values_list('primary_constituency', flat=True).distinct())
        
        if BasePolicy.is_regional_level(user):
            # Access to constituencies in assigned region
            from farms.models import Farm
            return list(
                Farm.objects.filter(region=user.region)
                .values_list('primary_constituency', flat=True)
                .distinct()
            )
        
        if BasePolicy.is_constituency_level(user):
            # Access to own constituency only
            return [user.constituency] if user.constituency else []
        
        return []
    
    @staticmethod
    def is_in_user_jurisdiction(user, constituency):
        """
        Check if constituency is within user's jurisdiction.
        
        Args:
            user: User instance
            constituency: Constituency name
        
        Returns:
            Boolean indicating if constituency is in jurisdiction
        """
        allowed_constituencies = BasePolicy.get_user_constituencies(user)
        return constituency in allowed_constituencies
    
    @staticmethod
    def is_active_investigation(user, resource):
        """
        Check if resource is part of user's active investigation.
        Used for auditor access.
        
        Args:
            user: User instance (must be auditor)
            resource: Resource being investigated
        
        Returns:
            Boolean indicating if user is investigating this resource
        """
        if not BasePolicy.is_auditor(user):
            return False
        
        # Check if there's an active fraud alert assigned to this user
        if hasattr(resource, 'farm'):
            farm = resource.farm
        elif hasattr(resource, '__class__') and resource.__class__.__name__ == 'Farm':
            farm = resource
        else:
            return False
        
        # Check for active fraud investigation
        from sales_revenue.models import FraudAlert
        return FraudAlert.objects.filter(
            farm=farm,
            reviewed_by=user,
            status='under_review'
        ).exists()
    
    @classmethod
    def scope(cls, user, queryset):
        """
        Filter queryset based on user's access level.
        Override in subclasses for model-specific scoping.
        
        Args:
            user: User instance
            queryset: Base queryset to filter
        
        Returns:
            Filtered queryset
        """
        raise NotImplementedError("Subclasses must implement scope() method")
    
    @classmethod
    def can_view(cls, user, resource):
        """Check if user can view resource."""
        raise NotImplementedError("Subclasses must implement can_view() method")
    
    @classmethod
    def can_create(cls, user, resource_class):
        """Check if user can create new resource."""
        raise NotImplementedError("Subclasses must implement can_create() method")
    
    @classmethod
    def can_edit(cls, user, resource):
        """Check if user can edit resource."""
        raise NotImplementedError("Subclasses must implement can_edit() method")
    
    @classmethod
    def can_delete(cls, user, resource):
        """Check if user can delete resource."""
        raise NotImplementedError("Subclasses must implement can_delete() method")
    
    @classmethod
    def editable_fields(cls, user, resource):
        """
        Get list of fields user can edit on resource.
        
        Args:
            user: User instance
            resource: Resource instance
        
        Returns:
            List of field names, or '__all__' for all fields
        """
        if cls.can_edit(user, resource):
            return '__all__'
        return []
