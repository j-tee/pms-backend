"""
Authorization Policies (CanCanCan-style)

This module provides policy classes for resource-level authorization.
Each policy defines what actions users can perform on specific resources.
"""

from .base_policy import BasePolicy
from .farm_policy import FarmPolicy
from .application_policy import ApplicationPolicy
from .sales_policy import SalesPolicy
from .production_policy import ProductionPolicy
from .inventory_policy import InventoryPolicy
from .batch_policy import BatchPolicy
from .user_policy import UserPolicy
from .procurement_policy import ProcurementPolicy

# Policy registry maps model names to their policy classes
POLICY_REGISTRY = {
    'Farm': FarmPolicy,
    'FarmApplication': ApplicationPolicy,
    'ApplicationQueue': ApplicationPolicy,
    'EggSale': SalesPolicy,
    'BirdSale': SalesPolicy,
    'Payment': SalesPolicy,
    'FarmerPayout': SalesPolicy,
    'Flock': ProductionPolicy,
    'DailyProduction': ProductionPolicy,
    'MortalityRecord': ProductionPolicy,
    'FeedInventory': InventoryPolicy,
    'FeedPurchase': InventoryPolicy,
    'Batch': BatchPolicy,
    'BatchEnrollmentApplication': BatchPolicy,
    'User': UserPolicy,
    # Procurement models
    'ProcurementOrder': ProcurementPolicy,
    'OrderAssignment': ProcurementPolicy,
    'DeliveryConfirmation': ProcurementPolicy,
    'ProcurementInvoice': ProcurementPolicy,
}


def get_policy_for_resource(resource):
    """
    Get the appropriate policy class for a resource.
    
    Args:
        resource: Model instance or class
    
    Returns:
        Policy class or None if no policy registered
    """
    if isinstance(resource, type):
        resource_type = resource.__name__
    else:
        resource_type = resource.__class__.__name__
    
    return POLICY_REGISTRY.get(resource_type)


def authorize(user, action, resource):
    """
    Check if user can perform action on resource.
    
    Args:
        user: User instance
        action: Action name (e.g., 'view', 'edit', 'delete')
        resource: Resource instance
    
    Returns:
        Boolean indicating if action is allowed
    """
    policy_class = get_policy_for_resource(resource)
    
    if not policy_class:
        # No policy defined, deny by default
        return False
    
    # Get the method name (e.g., 'can_view', 'can_edit')
    method_name = f'can_{action}'
    method = getattr(policy_class, method_name, None)
    
    if not method:
        # Method not defined, deny by default
        return False
    
    return method(user, resource)


__all__ = [
    'BasePolicy',
    'FarmPolicy',
    'ApplicationPolicy',
    'SalesPolicy',
    'ProductionPolicy',
    'InventoryPolicy',
    'BatchPolicy',
    'UserPolicy',
    'ProcurementPolicy',
    'get_policy_for_resource',
    'authorize',
]
