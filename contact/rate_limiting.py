"""
Rate Limiting Utilities for Contact Form

Prevents spam and abuse of the contact form.
"""
from functools import wraps
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
from rest_framework.response import Response
from rest_framework import status
from .models import ContactFormRateLimit


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(identifier, identifier_type, max_count, window_hours):
    """
    Check if identifier has exceeded rate limit.
    
    Args:
        identifier: IP address or email
        identifier_type: 'ip' or 'email'
        max_count: Maximum allowed submissions
        window_hours: Time window in hours
    
    Returns:
        tuple: (is_allowed, retry_after_seconds)
    """
    now = timezone.now()
    window_start = now - timedelta(hours=window_hours)
    
    try:
        rate_limit = ContactFormRateLimit.objects.get(
            identifier=identifier,
            identifier_type=identifier_type
        )
        
        # Check if window has expired
        if rate_limit.window_start < window_start:
            # Reset the window
            rate_limit.count = 0
            rate_limit.window_start = now
            rate_limit.save()
        
        # Check if limit exceeded
        if rate_limit.count >= max_count:
            # Calculate retry after
            window_end = rate_limit.window_start + timedelta(hours=window_hours)
            retry_after = (window_end - now).total_seconds()
            return False, int(retry_after)
        
    except ContactFormRateLimit.DoesNotExist:
        # Create new rate limit entry
        ContactFormRateLimit.objects.create(
            identifier=identifier,
            identifier_type=identifier_type,
            count=0,
            window_start=now
        )
    
    return True, 0


def increment_rate_limit(identifier, identifier_type):
    """Increment the rate limit counter."""
    rate_limit, created = ContactFormRateLimit.objects.get_or_create(
        identifier=identifier,
        identifier_type=identifier_type,
        defaults={'count': 0, 'window_start': timezone.now()}
    )
    
    rate_limit.count += 1
    rate_limit.save()


def rate_limit_contact_form(max_per_hour=5, max_per_day_email=20):
    """
    Decorator for rate limiting contact form submissions.
    
    Args:
        max_per_hour: Maximum submissions per IP per hour
        max_per_day_email: Maximum submissions per email per day
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(self, request, *args, **kwargs):
            # Get IP and email
            ip = get_client_ip(request)
            email = request.data.get('email')
            
            # Check IP rate limit (per hour)
            ip_allowed, ip_retry = check_rate_limit(ip, 'ip', max_per_hour, 1)
            if not ip_allowed:
                return Response(
                    {
                        'success': False,
                        'error': 'Too many submissions. Please try again later.',
                        'retry_after': ip_retry
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={'Retry-After': str(ip_retry)}
                )
            
            # Check email rate limit (per day)
            if email:
                email_allowed, email_retry = check_rate_limit(
                    email, 'email', max_per_day_email, 24
                )
                if not email_allowed:
                    return Response(
                        {
                            'success': False,
                            'error': 'Too many submissions from this email. Please try again tomorrow.',
                            'retry_after': email_retry
                        },
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                        headers={'Retry-After': str(email_retry)}
                    )
            
            # Proceed with the view
            response = view_func(self, request, *args, **kwargs)
            
            # If submission successful, increment counters
            if response.status_code == status.HTTP_201_CREATED:
                increment_rate_limit(ip, 'ip')
                if email:
                    increment_rate_limit(email, 'email')
            
            return response
        
        return wrapped_view
    return decorator
