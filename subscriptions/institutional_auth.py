"""
Authentication and permissions for Institutional API.

Supports DUAL AUTHENTICATION:
1. JWT Token (for web dashboard users - INSTITUTIONAL_SUBSCRIBER role)
2. API Key (for programmatic access - external scripts/systems)

Both methods provide access to the same endpoints but are used in different contexts.
"""

from rest_framework import authentication, permissions, exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
import time

from .institutional_models import InstitutionalAPIKey, InstitutionalAPIUsage

User = get_user_model()


class DualAuthentication(authentication.BaseAuthentication):
    """
    Dual authentication: Accepts BOTH JWT tokens AND API keys.
    
    Priority:
    1. Try JWT authentication first (for web dashboard)
    2. Fall back to API key authentication (for external API calls)
    
    JWT Usage (Web Dashboard):
        Authorization: Bearer <jwt_token>
        - User must have INSTITUTIONAL_SUBSCRIBER role
        - Extracts subscriber from user.institutional_subscriber
    
    API Key Usage (Programmatic):
        Authorization: ApiKey yea_xxxxx...
        - Validates API key against database
        - Rate limits based on subscription plan
    """
    
    def authenticate(self, request):
        """
        Authenticate request using JWT or API Key.
        Returns (user_or_subscriber, auth_token) or None.
        """
        # Try JWT first
        jwt_auth = JWTAuthentication()
        try:
            jwt_result = jwt_auth.authenticate(request)
            if jwt_result:
                user, token = jwt_result
                
                # Verify user has INSTITUTIONAL_SUBSCRIBER role
                if user.role != User.UserRole.INSTITUTIONAL_SUBSCRIBER:
                    raise exceptions.AuthenticationFailed(
                        'This endpoint requires INSTITUTIONAL_SUBSCRIBER role'
                    )
                
                # Verify user has linked subscriber
                if not user.institutional_subscriber:
                    raise exceptions.AuthenticationFailed(
                        'User account not linked to institutional subscriber'
                    )
                
                # Check subscriber is active
                if not user.institutional_subscriber.is_active:
                    raise exceptions.AuthenticationFailed(
                        'Subscription is not active. Please renew your subscription.'
                    )
                
                # Store subscriber and auth method on request
                # Store on both DRF request and underlying Django request for middleware access
                request.institutional_subscriber = user.institutional_subscriber
                request.auth_method = 'jwt'
                request.authenticated_user = user
                if hasattr(request, '_request'):
                    request._request.institutional_subscriber = user.institutional_subscriber
                    request._request.auth_method = 'jwt'
                    request._request.authenticated_user = user
                
                return (user, token)
        except exceptions.AuthenticationFailed:
            # JWT failed, try API key
            pass
        
        # Try API Key authentication
        api_key_value = self._get_api_key(request)
        
        if not api_key_value:
            return None  # No authentication provided
        
        api_key_obj, subscriber = InstitutionalAPIKey.verify_key(api_key_value)
        
        if not api_key_obj:
            raise exceptions.AuthenticationFailed('Invalid or expired API key')
        
        # Check IP whitelist
        if api_key_obj.allowed_ips:
            client_ip = self._get_client_ip(request)
            if client_ip not in api_key_obj.allowed_ips:
                raise exceptions.AuthenticationFailed(
                    f'IP address {client_ip} not authorized for this API key'
                )
        
        # Store API key and subscriber on request
        # Store on both DRF request and underlying Django request for middleware access
        request.institutional_api_key = api_key_obj
        request.institutional_subscriber = subscriber
        request.auth_method = 'api_key'
        if hasattr(request, '_request'):
            request._request.institutional_api_key = api_key_obj
            request._request.institutional_subscriber = subscriber
            request._request.auth_method = 'api_key'
        
        # Record API key usage (async task would be better in production)
        api_key_obj.record_usage(ip_address=self._get_client_ip(request))
        
        # Return subscriber as the "user" for permission checks
        # Note: subscriber is not a User object, so some features won't work
        return (subscriber, api_key_obj)
    
    def _get_api_key(self, request):
        """Extract API key from Authorization header, X-API-Key header, or query parameter"""
        # Check Authorization header (format: "ApiKey yea_xxxxx...")
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.lower().startswith('apikey '):
            return auth_header[7:].strip()
        
        # Check X-API-Key header (alternative format)
        api_key_header = request.META.get('HTTP_X_API_KEY', '')
        if api_key_header:
            return api_key_header.strip()
        
        # Fall back to query parameter (less secure, but convenient for testing)
        return request.query_params.get('api_key', None)
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class IsInstitutionalSubscriber(permissions.BasePermission):
    """
    Permission check for institutional API endpoints.
    Requires valid API key with active subscription OR JWT-authenticated institutional user.
    """
    
    def has_permission(self, request, view):
        # Check if authenticated via API key (subscriber set by DualAuthentication)
        subscriber = getattr(request, 'institutional_subscriber', None)
        
        # If not set by DualAuthentication, check if user is JWT-authenticated with INSTITUTIONAL_SUBSCRIBER role
        if not subscriber and request.user and request.user.is_authenticated:
            if request.user.role == 'INSTITUTIONAL_SUBSCRIBER' and hasattr(request.user, 'institutional_subscriber'):
                subscriber = request.user.institutional_subscriber
                # Set on request for consistency
                request.institutional_subscriber = subscriber
        
        if not subscriber:
            return False
        
        if not subscriber.is_active:
            raise exceptions.PermissionDenied(
                'Subscription is not active. Please renew your subscription.'
            )
        
        return True


class InstitutionalRateLimiter:
    """
    Rate limiter for institutional API based on subscription plan.
    Uses Redis cache for distributed rate limiting.
    """
    
    CACHE_PREFIX = 'inst_rate:'
    
    @classmethod
    def check_rate_limit(cls, subscriber, api_key):
        """
        Check if request is within rate limits.
        Returns (allowed, remaining_daily, remaining_monthly)
        Raises RateLimitExceeded if over limit.
        """
        plan = subscriber.plan
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Daily limit
        daily_key = f"{cls.CACHE_PREFIX}daily:{subscriber.id}:{today}"
        daily_count = cache.get(daily_key, 0)
        
        if daily_count >= plan.requests_per_day:
            raise RateLimitExceeded(
                f"Daily rate limit exceeded ({plan.requests_per_day} requests/day). "
                f"Resets at midnight UTC."
            )
        
        # Monthly limit
        monthly_key = f"{cls.CACHE_PREFIX}monthly:{subscriber.id}:{month_start}"
        monthly_count = cache.get(monthly_key, 0)
        
        if monthly_count >= plan.requests_per_month:
            raise RateLimitExceeded(
                f"Monthly rate limit exceeded ({plan.requests_per_month} requests/month). "
                f"Resets on {(month_start.replace(day=28) + timezone.timedelta(days=4)).replace(day=1)}."
            )
        
        # Increment counters
        # Daily expires at midnight
        seconds_until_midnight = cls._seconds_until_midnight()
        cache.set(daily_key, daily_count + 1, timeout=seconds_until_midnight)
        
        # Monthly expires at end of month (31 days max)
        cache.set(monthly_key, monthly_count + 1, timeout=31 * 24 * 60 * 60)
        
        return (
            True,
            plan.requests_per_day - daily_count - 1,
            plan.requests_per_month - monthly_count - 1
        )
    
    @classmethod
    def get_usage(cls, subscriber):
        """Get current usage counts"""
        plan = subscriber.plan
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        daily_key = f"{cls.CACHE_PREFIX}daily:{subscriber.id}:{today}"
        monthly_key = f"{cls.CACHE_PREFIX}monthly:{subscriber.id}:{month_start}"
        
        daily_count = cache.get(daily_key, 0)
        monthly_count = cache.get(monthly_key, 0)
        
        return {
            'daily_used': daily_count,
            'daily_limit': plan.requests_per_day,
            'daily_remaining': max(0, plan.requests_per_day - daily_count),
            'monthly_used': monthly_count,
            'monthly_limit': plan.requests_per_month,
            'monthly_remaining': max(0, plan.requests_per_month - monthly_count),
        }
    
    @classmethod
    def increment_counters(cls, subscriber):
        """Increment usage counters after a successful request"""
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        daily_key = f"{cls.CACHE_PREFIX}daily:{subscriber.id}:{today}"
        monthly_key = f"{cls.CACHE_PREFIX}monthly:{subscriber.id}:{month_start}"
        
        daily_count = cache.get(daily_key, 0)
        monthly_count = cache.get(monthly_key, 0)
        
        # Daily expires at midnight
        seconds_until_midnight = cls._seconds_until_midnight()
        cache.set(daily_key, daily_count + 1, timeout=seconds_until_midnight)
        
        # Monthly expires at end of month (31 days max)
        cache.set(monthly_key, monthly_count + 1, timeout=31 * 24 * 60 * 60)
    
    @staticmethod
    def _seconds_until_midnight():
        """Calculate seconds until midnight UTC"""
        now = timezone.now()
        midnight = (now + timezone.timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return int((midnight - now).total_seconds())


class RateLimitExceeded(exceptions.APIException):
    """Rate limit exceeded exception"""
    status_code = 429
    default_detail = 'Rate limit exceeded'
    default_code = 'rate_limit_exceeded'


class InstitutionalAPIUsageMiddleware:
    """
    Middleware to enforce rate limits and track institutional API usage.
    
    IMPORTANT: This middleware enforces rate limits for institutional API endpoints.
    It runs AFTER authentication (so subscriber is on request) and:
    1. Checks rate limits BEFORE view processing
    2. Returns 429 if limits exceeded
    3. Adds rate limit headers to ALL responses
    
    Headers added:
    - X-RateLimit-Limit-Daily: Maximum requests per day
    - X-RateLimit-Remaining-Daily: Remaining requests today
    - X-RateLimit-Limit-Monthly: Maximum requests per month
    - X-RateLimit-Remaining-Monthly: Remaining requests this month
    - X-RateLimit-Reset-Daily: Seconds until daily limit resets
    """
    
    # Skip rate limiting for these paths (webhooks, payment verification)
    EXEMPT_PATHS = [
        '/api/institutional/webhooks/',
        '/api/institutional/pay/verify/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Check if this is an institutional API endpoint
        is_institutional_endpoint = (
            request.path.startswith('/api/institutional/') or
            request.path.startswith('/api/admin/institutional/')
        )
        
        if not is_institutional_endpoint:
            return self.get_response(request)
        
        # Check if this path is exempt from rate limiting
        is_exempt = any(request.path.startswith(path) for path in self.EXEMPT_PATHS)
        
        start_time = time.time()
        
        # Process request - this runs the view including authentication
        response = self.get_response(request)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Get subscriber from request (set by DualAuthentication)
        subscriber = getattr(request, 'institutional_subscriber', None)
        api_key = getattr(request, 'institutional_api_key', None)
        
        if subscriber:
            # Get usage stats
            usage = InstitutionalRateLimiter.get_usage(subscriber)
            plan = subscriber.plan
            
            # Check rate limits for API key auth (not exempt paths)
            # Only check if response was successful (not already an error)
            if api_key and not is_exempt and response.status_code < 400:
                # Check daily limit
                if usage['daily_used'] >= plan.requests_per_day:
                    return self._rate_limit_response(
                        f"Daily rate limit exceeded ({plan.requests_per_day} requests/day). "
                        f"Resets at midnight UTC.",
                        usage, subscriber
                    )
                
                # Check monthly limit
                if usage['monthly_used'] >= plan.requests_per_month:
                    today = timezone.now().date()
                    next_month = (today.replace(day=28) + timezone.timedelta(days=4)).replace(day=1)
                    return self._rate_limit_response(
                        f"Monthly rate limit exceeded ({plan.requests_per_month} requests/month). "
                        f"Resets on {next_month}.",
                        usage, subscriber
                    )
                
                # Increment rate limit counters (only for successful API calls)
                InstitutionalRateLimiter.increment_counters(subscriber)
                
                # Re-fetch usage after increment for accurate headers
                usage = InstitutionalRateLimiter.get_usage(subscriber)
            
            # Add rate limit headers to response (always, even for non-API-key auth)
            response['X-RateLimit-Limit-Daily'] = str(plan.requests_per_day)
            response['X-RateLimit-Remaining-Daily'] = str(usage['daily_remaining'])
            response['X-RateLimit-Limit-Monthly'] = str(plan.requests_per_month)
            response['X-RateLimit-Remaining-Monthly'] = str(usage['monthly_remaining'])
            response['X-RateLimit-Reset-Daily'] = str(InstitutionalRateLimiter._seconds_until_midnight())
            
            # Record detailed usage (for API key auth only)
            if api_key:
                client_ip = self._get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                
                # Create detailed usage record (async in production)
                try:
                    InstitutionalAPIUsage.objects.create(
                        subscriber=subscriber,
                        api_key=api_key,
                        endpoint=request.path,
                        method=request.method,
                        status_code=response.status_code,
                        response_time_ms=duration_ms,
                        ip_address=client_ip,
                        user_agent=user_agent[:500],  # Truncate
                        date=timezone.now().date(),
                    )
                except Exception as e:
                    # Don't fail the request if usage logging fails
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to record institutional API usage: {e}")
        
        return response
    
    def _rate_limit_response(self, message, usage, subscriber):
        """Generate a 429 Too Many Requests response with headers"""
        from django.http import JsonResponse
        
        response = JsonResponse(
            {
                'error': message,
                'code': 'rate_limit_exceeded',
                'detail': {
                    'daily_limit': usage['daily_limit'],
                    'daily_used': usage['daily_used'],
                    'monthly_limit': usage['monthly_limit'],
                    'monthly_used': usage['monthly_used'],
                }
            },
            status=429
        )
        
        # Add rate limit headers
        response['X-RateLimit-Limit-Daily'] = str(usage['daily_limit'])
        response['X-RateLimit-Remaining-Daily'] = '0'
        response['X-RateLimit-Limit-Monthly'] = str(usage['monthly_limit'])
        response['X-RateLimit-Remaining-Monthly'] = str(usage['monthly_remaining'])
        response['X-RateLimit-Reset-Daily'] = str(InstitutionalRateLimiter._seconds_until_midnight())
        
        return response
    
    def _get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class HasDataAccess(permissions.BasePermission):
    """
    Check if subscriber has access to specific data type based on plan.
    
    Usage:
        class MyView(APIView):
            permission_classes = [IsInstitutionalSubscriber, HasDataAccess]
            required_access = 'access_mortality_data'  # Plan field to check
    """
    
    def has_permission(self, request, view):
        subscriber = getattr(request, 'institutional_subscriber', None)
        
        # If not set by DualAuthentication, check if user is JWT-authenticated
        if not subscriber and request.user and request.user.is_authenticated:
            if request.user.role == 'INSTITUTIONAL_SUBSCRIBER' and hasattr(request.user, 'institutional_subscriber'):
                subscriber = request.user.institutional_subscriber
                request.institutional_subscriber = subscriber
        
        if not subscriber:
            return False
        
        required_access = getattr(view, 'required_access', None)
        if not required_access:
            return True  # No specific access required
        
        plan = subscriber.plan
        if not getattr(plan, required_access, False):
            raise exceptions.PermissionDenied(
                f"Your plan ({plan.name}) does not include access to this data. "
                f"Please upgrade to access this feature."
            )
        
        return True


class IsInstitutionalAdmin(permissions.BasePermission):
    """
    Permission for admin endpoints that manage institutional subscribers.
    
    SECURITY: Institutional subscriptions are B2B business between institutions
    and the platform (Alphalogique). Only platform staff (SUPER_ADMIN) should
    have access to this data, NOT YEA government officials.
    
    Allowed roles:
    - SUPER_ADMIN (Platform Owner - Alphalogique)
    
    NOT allowed:
    - NATIONAL_ADMIN, REGIONAL_ADMIN, etc. (YEA government - they are clients)
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # ONLY allow platform staff (SUPER_ADMIN)
        # YEA government officials are clients and should NOT see institutional data
        if request.user.role != User.UserRole.SUPER_ADMIN:
            raise exceptions.PermissionDenied(
                'Only platform administrators can access institutional subscription data'
            )
        
        return True


def require_rate_limit_check(view_func):
    """
    Decorator to enforce rate limiting on institutional API views.
    
    Usage:
        @require_rate_limit_check
        def get(self, request):
            ...
    """
    def wrapper(self, request, *args, **kwargs):
        subscriber = getattr(request, 'institutional_subscriber', None)
        api_key = getattr(request, 'institutional_api_key', None)
        
        if subscriber and api_key:
            # Check rate limit (raises RateLimitExceeded if exceeded)
            InstitutionalRateLimiter.check_rate_limit(subscriber, api_key)
        
        return view_func(self, request, *args, **kwargs)
    
    return wrapper
