"""
Inventory Authorization Policy

Defines access control rules for inventory models.
"""

from .base_policy import BasePolicy


class InventoryPolicy(BasePolicy):
    """Authorization policy for inventory models."""
    
    @classmethod
    def can_view(cls, user, resource):
        """
        Check if user can view inventory record.
        
        Access Rules:
        - Farmer: Own inventory
        - Extension Officer: Assigned farms
        - Procurement Officer: All inventory
        - Officials: Based on farm access
        """
        # Procurement officer can view all
        if cls.is_procurement_officer(user):
            return True
        
        # Get farm from resource
        farm = resource.farm
        
        # Use FarmPolicy for farm-based access
        from .farm_policy import FarmPolicy
        return FarmPolicy.can_view(user, farm)
    
    @classmethod
    def can_create(cls, user, farm):
        """
        Check if user can create inventory record.
        
        Access Rules:
        - Farmer: Own farm
        - Procurement Officer: Any farm (for distribution)
        """
        if cls.is_farmer(user):
            return farm.owner == user
        
        if cls.is_procurement_officer(user):
            return True
        
        return cls.is_super_admin(user)
    
    @classmethod
    def can_edit(cls, user, resource):
        """
        Check if user can edit inventory record.
        
        Access Rules:
        - Farmer: Own records
        - Procurement Officer: Any records
        """
        if cls.is_super_admin(user):
            return True
        
        if cls.is_procurement_officer(user):
            return True
        
        if cls.is_farmer(user):
            return resource.farm.owner == user
        
        return False
    
    @classmethod
    def can_delete(cls, user, resource):
        """Only super admin can delete."""
        return cls.is_super_admin(user)
    
    @classmethod
    def can_create_purchase_order(cls, user):
        """
        Check if user can create purchase order.
        
        Access Rules:
        - Procurement Officer
        - National Admin
        """
        return cls.is_procurement_officer(user) or cls.is_national_admin(user)
    
    @classmethod
    def can_distribute_supplies(cls, user):
        """
        Check if user can distribute supplies to farms.
        
        Access Rules:
        - Procurement Officer
        """
        return cls.is_procurement_officer(user)
    
    @classmethod
    def scope(cls, user, queryset=None):
        """Filter inventory records based on user's access."""
        if queryset is None:
            raise ValueError("Must provide queryset")
        
        # Procurement officer sees all
        if cls.is_procurement_officer(user):
            return queryset
        
        # Others see based on farm access
        from .farm_policy import FarmPolicy
        accessible_farms = FarmPolicy.scope(user)
        
        return queryset.filter(farm__in=accessible_farms)
