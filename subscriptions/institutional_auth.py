"""
Authentication and permissions for Institutional API.
"""

from rest_framework import authentication, permissions, exceptions
from django.utils import timezone
from django.core.cache import cache
import time

from .institutional_models import InstitutionalAPIKey, InstitutionalAPIUsage


class InstitutionalAPIKeyAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for institutional API keys.
    
    Usage:
        Add header: Authorization: ApiKey yea_xxxxx...
        
    Or query parameter (less secure):
        ?api_key=yea_xxxxx...
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using API key.
        Returns (None, None) if no API key provided (allows other auth methods).
        """
        api_key = self._get_api_key(request)
        
        if not api_key:
            return None  # No API key, try other auth methods
        
        api_key_obj, subscriber = InstitutionalAPIKey.verify_key(api_key)
        
        if not api_key_obj:
            raise exceptions.AuthenticationFailed('Invalid or expired API key')
        
        # Check IP whitelist
        if api_key_obj.allowed_ips:
            client_ip = self._get_client_ip(request)
            if client_ip not in api_key_obj.allowed_ips:
                raise exceptions.AuthenticationFailed(
                    f'IP address {client_ip} not authorized for this API key'
                )
        
        # Store API key on request for rate limiting and usage tracking
        request.institutional_api_key = api_key_obj
        request.institutional_subscriber = subscriber
        
        # Return subscriber as the "user" for this request
        return (subscriber, api_key_obj)
    
    def _get_api_key(self, request):
        """Extract API key from header or query parameter"""
        # Check Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.lower().startswith('apikey '):
            return auth_header[7:].strip()
        
        # Fall back to query parameter
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
    Requires valid API key with active subscription.
    """
    
    def has_permission(self, request, view):
        # Check if authenticated via API key
        subscriber = getattr(request, 'institutional_subscriber', None)
        
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
    Middleware to track institutional API usage.
    Records each request for billing and analytics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Only track institutional API endpoints
        if not request.path.startswith('/api/institutional/'):
            return self.get_response(request)
        
        start_time = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record usage if authenticated with API key
        subscriber = getattr(request, 'institutional_subscriber', None)
        api_key = getattr(request, 'institutional_api_key', None)
        
        if subscriber and api_key:
            # Update API key usage
            client_ip = self._get_client_ip(request)
            api_key.record_usage(ip_address=client_ip)
            
            # Create usage record (async in production)
            InstitutionalAPIUsage.objects.create(
                subscriber=subscriber,
                api_key=api_key,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=duration_ms,
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                date=timezone.now().date(),
            )
        
        # Add rate limit headers
        if subscriber:
            usage = InstitutionalRateLimiter.get_usage(subscriber)
            response['X-RateLimit-Limit-Daily'] = usage['daily_limit']
            response['X-RateLimit-Remaining-Daily'] = usage['daily_remaining']
            response['X-RateLimit-Limit-Monthly'] = usage['monthly_limit']
            response['X-RateLimit-Remaining-Monthly'] = usage['monthly_remaining']
        
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
