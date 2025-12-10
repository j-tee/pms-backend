"""
Base Policy Class

Provides common authorization methods for all policy classes.
"""


class BasePolicy:
    """
    Base class for all authorization policies.
    Provides helper methods for common permission checks.
    """
    
    @staticmethod
    def is_super_admin(user):
        """Check if user is super admin (highest privilege level)."""
        return user.role == 'SUPER_ADMIN' or user.has_role('SUPER_ADMIN')
    
    @staticmethod
    def is_yea_official(user):
        """Check if user is YEA official (elevated admin below super admin)."""
        return user.role == 'YEA_OFFICIAL' or user.has_role('YEA_OFFICIAL')
    
    @staticmethod
    def is_national_admin(user):
        """Check if user is national admin."""
        return user.role == 'NATIONAL_ADMIN' or user.has_role('NATIONAL_ADMIN')
    
    @staticmethod
    def is_regional_coordinator(user):
        """Check if user is regional coordinator."""
        return user.role == 'REGIONAL_COORDINATOR' or user.has_role('REGIONAL_COORDINATOR')
    
    @staticmethod
    def is_constituency_official(user):
        """Check if user is constituency official."""
        return user.role == 'CONSTITUENCY_OFFICIAL' or user.has_role('CONSTITUENCY_OFFICIAL')
    
    @staticmethod
    def is_extension_officer(user):
        """Check if user is extension officer."""
        return user.has_role('EXTENSION_OFFICER')
    
    @staticmethod
    def is_veterinary_officer(user):
        """Check if user is veterinary officer."""
        return user.has_role('VETERINARY_OFFICER')
    
    @staticmethod
    def is_procurement_officer(user):
        """Check if user is procurement officer."""
        return user.has_role('PROCUREMENT_OFFICER')
    
    @staticmethod
    def is_auditor(user):
        """Check if user is auditor."""
        return user.has_role('AUDITOR')
    
    @staticmethod
    def is_finance_officer(user):
        """Check if user is finance officer."""
        return user.has_role('FINANCE_OFFICER')
    
    @staticmethod
    def is_farmer(user):
        """Check if user is farmer."""
        return user.has_role('FARMER')
    
    @staticmethod
    def has_admin_access(user):
        """Check if user has any admin-level access."""
        return (
            BasePolicy.is_super_admin(user) or
            BasePolicy.is_yea_official(user) or
            BasePolicy.is_national_admin(user) or
            BasePolicy.is_regional_coordinator(user) or
            BasePolicy.is_constituency_official(user)
        )
    
    @staticmethod
    def has_elevated_admin_access(user):
        """Check if user has elevated admin access (Super Admin or YEA Official)."""
        return BasePolicy.is_super_admin(user) or BasePolicy.is_yea_official(user)
    
    @staticmethod
    def get_user_constituencies(user):
        """
        Get list of constituencies user has access to.
        
        Returns:
            List of constituency names
        """
        if BasePolicy.is_super_admin(user) or BasePolicy.is_yea_official(user) or BasePolicy.is_national_admin(user):
            # Access to all constituencies
            from farms.models import Farm
            return list(Farm.objects.values_list('primary_constituency', flat=True).distinct())
        
        if BasePolicy.is_regional_coordinator(user):
            # Access to constituencies in assigned region
            from farms.models import Farm
            # Assuming user.region is set
            return list(
                Farm.objects.filter(region=user.region)
                .values_list('primary_constituency', flat=True)
                .distinct()
            )
        
        if BasePolicy.is_constituency_official(user):
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
