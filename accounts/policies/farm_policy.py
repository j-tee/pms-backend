"""
Farm Authorization Policy

Defines access control rules for Farm model.
"""

from django.db.models import Q
from .base_policy import BasePolicy


class FarmPolicy(BasePolicy):
    """Authorization policy for Farm model."""
    
    @classmethod
    def can_view(cls, user, farm):
        """
        Check if user can view specific farm.
        
        Access Rules:
        - Super Admin: All farms
        - National Admin: All farms
        - Regional Coordinator: Farms in their region
        - Constituency Official: Farms in their constituency
        - Extension Officer: Assigned farms only
        - Veterinary Officer: Farms in their jurisdiction
        - Auditor: Farms under active investigation
        - Farmer: Own farm only
        """
        # Super admin and national admin can view all
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        # Auditor can view if investigating
        if cls.is_auditor(user) and cls.is_active_investigation(user, farm):
            return True
        
        # Regional coordinator can view farms in their region
        if cls.is_regional_coordinator(user):
            return cls.is_in_user_jurisdiction(user, farm.primary_constituency)
        
        # Constituency official can view farms in their constituency
        if cls.is_constituency_official(user):
            return farm.primary_constituency == user.constituency
        
        # Extension officer can view assigned farms only
        if cls.is_extension_officer(user):
            return (
                farm.extension_officer == user or
                farm.assigned_extension_officer == user
            )
        
        # Veterinary officer can view farms in jurisdiction
        if cls.is_veterinary_officer(user):
            return cls.is_in_user_jurisdiction(user, farm.primary_constituency)
        
        # Farmer can view own farm only
        if cls.is_farmer(user):
            return farm.owner == user
        
        return False
    
    @classmethod
    def can_create(cls, user, resource_class):
        """
        Check if user can create new farm.
        
        Access Rules:
        - Only through application approval process
        - System creates farms automatically after approval
        """
        # Only super admin or national admin can manually create farms
        return cls.is_super_admin(user) or cls.is_national_admin(user)
    
    @classmethod
    def can_edit(cls, user, farm):
        """
        Check if user can edit specific farm.
        
        Access Rules:
        - Super Admin: Can edit all fields
        - National Admin: Can edit most fields
        - Constituency Official: Limited fields
        - Farmer: Very limited fields (profile only)
        """
        # Super admin can edit all
        if cls.is_super_admin(user):
            return True
        
        # National admin can edit most fields
        if cls.is_national_admin(user):
            return True
        
        # Constituency official can edit limited fields
        if cls.is_constituency_official(user):
            return farm.primary_constituency == user.constituency
        
        # Farmer can edit own farm (limited fields only)
        if cls.is_farmer(user):
            return farm.owner == user
        
        return False
    
    @classmethod
    def can_delete(cls, user, farm):
        """
        Check if user can delete farm.
        
        Access Rules:
        - Only super admin can delete farms
        - Deletion creates audit trail
        """
        return cls.is_super_admin(user)
    
    @classmethod
    def can_suspend(cls, user, farm):
        """Check if user can suspend farm."""
        return cls.is_super_admin(user) or cls.is_national_admin(user)
    
    @classmethod
    def can_activate(cls, user, farm):
        """Check if user can activate farm."""
        return cls.is_super_admin(user) or cls.is_national_admin(user)
    
    @classmethod
    def can_assign_extension_officer(cls, user, farm):
        """Check if user can assign extension officer to farm."""
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return True
        
        if cls.is_regional_coordinator(user):
            return cls.is_in_user_jurisdiction(user, farm.primary_constituency)
        
        if cls.is_constituency_official(user):
            return farm.primary_constituency == user.constituency
        
        return False
    
    @classmethod
    def can_view_financial_data(cls, user, farm):
        """Check if user can view farm financial data."""
        # Admin roles can view financial data
        if cls.has_admin_access(user):
            return cls.can_view(user, farm)
        
        # Auditor can view if investigating
        if cls.is_auditor(user):
            return cls.is_active_investigation(user, farm)
        
        # Finance officer can view all financial data
        if cls.is_finance_officer(user):
            return True
        
        # Farmer can view own financial data
        if cls.is_farmer(user):
            return farm.owner == user
        
        return False
    
    @classmethod
    def can_enable_marketplace(cls, user, farm):
        """Check if user can enable marketplace for farm."""
        # Only farmer can enable/disable their own marketplace
        if cls.is_farmer(user) and farm.owner == user:
            return True
        
        # Admins can enable/disable
        return cls.is_super_admin(user) or cls.is_national_admin(user)
    
    @classmethod
    def editable_fields(cls, user, farm):
        """
        Get list of fields user can edit.
        
        Returns:
            List of field names or '__all__' for all fields
        """
        if cls.is_super_admin(user):
            return '__all__'
        
        if cls.is_national_admin(user):
            # Can edit most fields except critical system fields
            return [
                'farm_name', 'alternate_phone', 'email',
                'preferred_contact_method', 'residential_address',
                'number_of_poultry_houses', 'total_bird_capacity',
                'current_bird_count', 'housing_type',
                'primary_production_type', 'monthly_operating_budget',
                'expected_monthly_revenue', 'farm_status',
                'extension_officer', 'assigned_extension_officer',
                'marketplace_enabled'
            ]
        
        if cls.is_constituency_official(user):
            return [
                'extension_officer',
                'assigned_extension_officer',
                'current_bird_count',
                'number_of_poultry_houses'
            ]
        
        if cls.is_farmer(user) and farm.owner == user:
            # Farmers can only edit profile fields
            return [
                'farm_name',
                'alternate_phone',
                'email',
                'preferred_contact_method',
                'current_bird_count',
                'monthly_operating_budget',
                'expected_monthly_revenue'
            ]
        
        return []
    
    @classmethod
    def scope(cls, user, queryset=None):
        """
        Filter farms based on user's access level.
        
        Args:
            user: User instance
            queryset: Optional base queryset
        
        Returns:
            Filtered queryset
        """
        if queryset is None:
            from farms.models import Farm
            queryset = Farm.objects.all()
        
        # Super admin and national admin see all
        if cls.is_super_admin(user) or cls.is_national_admin(user):
            return queryset
        
        # Regional coordinator sees farms in their region
        if cls.is_regional_coordinator(user):
            constituencies = cls.get_user_constituencies(user)
            return queryset.filter(primary_constituency__in=constituencies)
        
        # Constituency official sees farms in their constituency
        if cls.is_constituency_official(user):
            return queryset.filter(primary_constituency=user.constituency)
        
        # Extension officer sees assigned farms only
        if cls.is_extension_officer(user):
            return queryset.filter(
                Q(extension_officer=user) | Q(assigned_extension_officer=user)
            )
        
        # Veterinary officer sees farms in jurisdiction
        if cls.is_veterinary_officer(user):
            constituencies = cls.get_user_constituencies(user)
            return queryset.filter(primary_constituency__in=constituencies)
        
        # Auditor sees farms under investigation
        if cls.is_auditor(user):
            from sales_revenue.models import FraudAlert
            farm_ids = FraudAlert.objects.filter(
                reviewed_by=user,
                status='under_review'
            ).values_list('farm_id', flat=True)
            return queryset.filter(id__in=farm_ids)
        
        # Farmer sees own farm only
        if cls.is_farmer(user):
            return queryset.filter(owner=user)
        
        # Default: no access
        return queryset.none()
