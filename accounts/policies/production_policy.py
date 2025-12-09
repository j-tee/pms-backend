"""
Production Authorization Policy

Defines access control rules for production-related models.
"""

from .base_policy import BasePolicy


class ProductionPolicy(BasePolicy):
    """Authorization policy for production models (Flock, DailyProduction, MortalityRecord)."""
    
    @classmethod
    def can_view(cls, user, resource):
        """
        Check if user can view production record.
        
        Access Rules:
        - Farmer: Own production records
        - Extension Officer: Assigned farms
        - Veterinary Officer: Jurisdiction farms
        - Officials: Based on farm access
        """
        # Get farm from resource
        farm = resource.farm
        
        # Use FarmPolicy to check farm access
        from .farm_policy import FarmPolicy
        return FarmPolicy.can_view(user, farm)
    
    @classmethod
    def can_create(cls, user, farm):
        """
        Check if user can create production record for farm.
        
        Access Rules:
        - Farmer: Own farm only
        """
        if cls.is_farmer(user):
            return farm.owner == user
        
        # Admins can create on behalf
        return cls.is_super_admin(user)
    
    @classmethod
    def can_edit(cls, user, resource):
        """
        Check if user can edit production record.
        
        Access Rules:
        - Farmer: Own records within edit window (24-48 hours)
        - Admins: Any record
        """
        if cls.is_super_admin(user):
            return True
        
        # Farmer can edit own records
        if cls.is_farmer(user) and resource.farm.owner == user:
            # Check if within edit window
            from django.utils import timezone
            from datetime import timedelta
            
            # Allow edit within 48 hours of creation
            edit_deadline = resource.recorded_at + timedelta(hours=48)
            return timezone.now() <= edit_deadline
        
        return False
    
    @classmethod
    def can_delete(cls, user, resource):
        """
        Check if user can delete production record.
        
        Access Rules:
        - Only super admin
        - Soft delete with audit trail
        """
        return cls.is_super_admin(user)
    
    @classmethod
    def can_investigate_mortality(cls, user, mortality_record):
        """
        Check if user can investigate mortality.
        
        Access Rules:
        - Veterinary officer in jurisdiction
        - Extension officer for assigned farms
        """
        farm = mortality_record.farm
        
        if cls.is_veterinary_officer(user):
            return cls.is_in_user_jurisdiction(user, farm.primary_constituency)
        
        if cls.is_extension_officer(user):
            return farm.extension_officer == user or farm.assigned_extension_officer == user
        
        # Admins can investigate
        return cls.has_admin_access(user)
    
    @classmethod
    def can_approve_compensation(cls, user, mortality_record):
        """
        Check if user can approve mortality compensation.
        
        Access Rules:
        - National admin only
        - Finance officer can process after approval
        """
        return cls.is_national_admin(user)
    
    @classmethod
    def scope(cls, user, queryset=None):
        """Filter production records based on user's access."""
        if queryset is None:
            # Would need to know which model
            raise ValueError("Must provide queryset")
        
        # Get accessible farms
        from .farm_policy import FarmPolicy
        accessible_farms = FarmPolicy.scope(user)
        
        # Filter records by accessible farms
        return queryset.filter(farm__in=accessible_farms)


# Convenience aliases
FlockPolicy = ProductionPolicy
DailyProductionPolicy = ProductionPolicy
MortalityRecordPolicy = ProductionPolicy
