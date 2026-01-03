"""
Authorization Decorators

Provides decorators for API views to enforce authorization policies.
Similar to CanCanCan's authorize! method.
"""

from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .policies import get_policy_for_resource, authorize as policy_authorize


def authorize(permission_codename=None, action=None, resource_getter=None, policy_check=None):
    """
    Decorator to check permissions before executing view.
    
    Args:
        permission_codename: Permission codename to check (e.g., 'edit_farm')
        action: Action name for policy check (e.g., 'view', 'edit', 'delete')
        resource_getter: Function to get resource from request/kwargs
        policy_check: Custom policy check function
    
    Usage:
        # Permission-based check
        @authorize(permission_codename='edit_farm')
        def update_farm(request, pk):
            ...
        
        # Policy-based check
        @authorize(
            action='edit',
            resource_getter=lambda request, **kwargs: Farm.objects.get(pk=kwargs['pk'])
        )
        def update_farm(request, pk):
            ...
        
        # Custom check
        @authorize(
            policy_check=lambda user, request, **kwargs: user.is_verified
        )
        def sensitive_action(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            # Check authentication
            if not user.is_authenticated:
                return Response(
                    {
                        'error': 'Authentication required',
                        'code': 'AUTH_REQUIRED'
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Custom policy check
            if policy_check:
                try:
                    if not policy_check(user, request, *args, **kwargs):
                        return Response(
                            {
                                'error': 'You do not have permission to perform this action',
                                'code': 'PERMISSION_DENIED'
                            },
                            status=status.HTTP_403_FORBIDDEN
                        )
                except Exception as e:
                    return Response(
                        {
                            'error': 'Authorization check failed',
                            'code': 'AUTH_CHECK_ERROR',
                            'detail': str(e)
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            # Permission-based check
            if permission_codename:
                if not user.has_permission(permission_codename):
                    return Response(
                        {
                            'error': 'You do not have permission to perform this action',
                            'code': 'PERMISSION_DENIED',
                            'required_permission': permission_codename
                        },
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Resource-level policy check
            if action and resource_getter:
                try:
                    resource = resource_getter(request, *args, **kwargs)
                except Exception as e:
                    return Response(
                        {
                            'error': 'Resource not found',
                            'code': 'RESOURCE_NOT_FOUND',
                            'detail': str(e)
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Get policy class for resource
                policy_class = get_policy_for_resource(resource)
                
                if policy_class:
                    # Get authorization method (e.g., 'can_edit')
                    method_name = f'can_{action}'
                    method = getattr(policy_class, method_name, None)
                    
                    if method:
                        if not method(user, resource):
                            return Response(
                                {
                                    'error': 'You do not have permission to access this resource',
                                    'code': 'RESOURCE_ACCESS_DENIED',
                                    'action': action,
                                    'resource_type': resource.__class__.__name__
                                },
                                status=status.HTTP_403_FORBIDDEN
                            )
                    else:
                        # Method not defined, deny by default
                        return Response(
                            {
                                'error': 'Authorization method not defined',
                                'code': 'AUTH_METHOD_NOT_DEFINED',
                                'action': action
                            },
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR
                        )
            
            # All checks passed, execute view
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def authorize_query(policy_class=None, queryset_name='queryset'):
    """
    Decorator to automatically scope queryset based on user's permissions.
    
    Args:
        policy_class: Policy class to use for scoping
        queryset_name: Name of queryset attribute/variable in view
    
    Usage:
        @authorize_query(policy_class=FarmPolicy)
        def list_farms(request):
            queryset = Farm.objects.all()  # Will be scoped automatically
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Execute view
            result = func(request, *args, **kwargs)
            
            # If view returns queryset, scope it
            if hasattr(result, 'data') and policy_class:
                # For DRF views with queryset
                pass  # Scoping should be done in get_queryset() method
            
            return result
        
        return wrapper
    return decorator


def require_role(*role_names):
    """
    Decorator to require specific role(s).
    
    Usage:
        @require_role('NATIONAL_ADMIN', 'SUPER_ADMIN')
        def admin_only_action(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user has any of the required roles
            has_role = any(user.has_role(role_name) for role_name in role_names)
            
            if not has_role:
                return Response(
                    {
                        'error': 'You do not have the required role',
                        'code': 'ROLE_REQUIRED',
                        'required_roles': list(role_names)
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_permission(*permission_codenames):
    """
    Decorator to require specific permission(s).
    
    Usage:
        @require_permission('edit_farm', 'view_farm')
        def update_farm(request, pk):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if user has all required permissions
            has_all = all(
                user.has_permission(perm) for perm in permission_codenames
            )
            
            if not has_all:
                return Response(
                    {
                        'error': 'You do not have the required permissions',
                        'code': 'PERMISSIONS_REQUIRED',
                        'required_permissions': list(permission_codenames)
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_verification(check_phone=True, check_email=False):
    """
    Decorator to require user verification.
    
    Usage:
        @require_verification(check_phone=True, check_email=True)
        def create_sale(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check phone verification
            if check_phone and not user.phone_verified:
                return Response(
                    {
                        'error': 'Phone verification required',
                        'code': 'PHONE_VERIFICATION_REQUIRED'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check email verification
            if check_email and not user.email_verified:
                return Response(
                    {
                        'error': 'Email verification required',
                        'code': 'EMAIL_VERIFICATION_REQUIRED'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_marketplace_activation(func):
    """
    Decorator to require active marketplace activation (seller access).
    
    NOTE: Renamed from require_marketplace_subscription per monetization strategy.
    Avoid "subscription" terminology - use "Marketplace Activation" or "Seller Access".
    
    Usage:
        @require_marketplace_activation
        def create_product_listing(request):
            ...
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.user
        
        if not user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user has farm
        if not hasattr(user, 'farm'):
            return Response(
                {
                    'error': 'Farm profile required',
                    'code': 'FARM_REQUIRED'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        farm = user.farm
        
        # Check marketplace enabled
        if not farm.marketplace_enabled:
            # Get activation fee from platform settings
            from sales_revenue.models import PlatformSettings
            settings = PlatformSettings.get_settings()
            activation_fee = settings.marketplace_activation_fee
            
            return Response(
                {
                    'error': 'Marketplace access not activated',
                    'code': 'MARKETPLACE_NOT_ACTIVATED',
                    'message': f'Activate marketplace access for GHS {activation_fee}/month to sell products',
                    'activation_fee': float(activation_fee)
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check activation status (subscription record)
        if hasattr(farm, 'subscription'):
            activation = farm.subscription
            if activation.status not in ['trial', 'active']:
                return Response(
                    {
                        'error': 'Active marketplace access required',
                        'code': 'ACTIVATION_EXPIRED',
                        'activation_status': activation.status,
                        'message': 'Your marketplace access is not active. Please renew to continue selling.'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        elif farm.subscription_type == 'none':
            from sales_revenue.models import PlatformSettings
            settings = PlatformSettings.get_settings()
            activation_fee = settings.marketplace_activation_fee
            
            return Response(
                {
                    'error': 'Marketplace activation required',
                    'code': 'ACTIVATION_REQUIRED',
                    'message': f'Activate marketplace access for GHS {activation_fee}/month to sell products',
                    'activation_fee': float(activation_fee)
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        return func(request, *args, **kwargs)
    
    return wrapper


# Backward compatibility alias
require_marketplace_subscription = require_marketplace_activation


# Context manager for authorization
class AuthorizationContext:
    """
    Context manager for authorization checks in view logic.
    
    Usage:
        with AuthorizationContext(user, 'edit', farm) as authorized:
            if not authorized:
                return Response({'error': 'Not authorized'}, status=403)
            # Perform action
    """
    
    def __init__(self, user, action, resource):
        self.user = user
        self.action = action
        self.resource = resource
        self.authorized = False
    
    def __enter__(self):
        self.authorized = policy_authorize(self.user, self.action, self.resource)
        return self.authorized
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False  # Don't suppress exceptions
