"""
Platform Settings Views

API views for super admin platform configuration management.
Provides REST API access to PlatformSettings (singleton).
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import PlatformSettings
from .platform_settings_serializers import (
    PlatformSettingsSerializer,
    MarketplaceMonetizationSerializer,
    PublicPlatformSettingsSerializer,
)


class IsSuperAdmin:
    """
    Permission check for super admin access.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role in ['SUPER_ADMIN', 'YEA_OFFICIAL']
        )


class PlatformSettingsView(APIView):
    """
    GET /api/admin/platform-settings/
    PUT /api/admin/platform-settings/
    PATCH /api/admin/platform-settings/
    
    Full platform settings management (Super Admin / YEA Official only).
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Super Admin or YEA Official access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = PlatformSettings.get_settings()
        serializer = PlatformSettingsSerializer(settings)
        return Response(serializer.data)
    
    def put(self, request):
        return self._update_settings(request, partial=False)
    
    def patch(self, request):
        return self._update_settings(request, partial=True)
    
    def _update_settings(self, request, partial=False):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Super Admin or YEA Official access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = PlatformSettings.get_settings()
        serializer = PlatformSettingsSerializer(settings, data=request.data, partial=partial)
        
        if serializer.is_valid():
            # Track who modified
            serializer.save(last_modified_by=request.user)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MarketplaceMonetizationView(APIView):
    """
    GET /api/admin/platform-settings/monetization/
    PATCH /api/admin/platform-settings/monetization/
    
    Marketplace monetization settings only (Super Admin / YEA Official).
    Focused subset for quick monetization config changes.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Super Admin or YEA Official access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = PlatformSettings.get_settings()
        serializer = MarketplaceMonetizationSerializer(settings)
        return Response(serializer.data)
    
    def patch(self, request):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Super Admin or YEA Official access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        settings = PlatformSettings.get_settings()
        serializer = MarketplaceMonetizationSerializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # Also update last_modified_by on the settings object
            settings.last_modified_by = request.user
            settings.save(update_fields=['last_modified_by', 'updated_at'])
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PublicPlatformSettingsView(APIView):
    """
    GET /api/public/platform-settings/
    
    Public-facing platform settings (no auth required).
    Returns non-sensitive settings for frontend display.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        settings = PlatformSettings.get_settings()
        serializer = PublicPlatformSettingsSerializer(settings)
        return Response(serializer.data)


class PlatformSettingsResetView(APIView):
    """
    POST /api/admin/platform-settings/reset/
    
    Reset platform settings to defaults (Super Admin only).
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Super Admin access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get current settings
        settings = PlatformSettings.get_settings()
        
        # Reset to defaults
        defaults = {
            # Commission
            'commission_tier_1_percentage': 5.0,
            'commission_tier_1_threshold': 100.0,
            'commission_tier_2_percentage': 3.0,
            'commission_tier_2_threshold': 500.0,
            'commission_tier_3_percentage': 2.0,
            'commission_minimum_amount': 2.0,
            # Paystack
            'paystack_fee_bearer': 'account',
            'paystack_settlement_schedule': 'auto',
            # Payment
            'payment_retry_max_attempts': 3,
            'payment_retry_delay_seconds': 300,
            # Refund
            'refund_eligibility_hours': 48,
            'payment_auto_refund_hours': 72,
            'enable_refunds': True,
            'enable_auto_refunds': True,
            'enable_instant_settlements': False,
            # Marketplace Activation (per monetization strategy)
            'marketplace_activation_fee': 50.00,
            'marketplace_trial_days': 14,
            'marketplace_grace_period_days': 5,
            # Government Subsidy
            'enable_government_subsidy': False,
            'government_subsidy_percentage': 100.0,
            # Transaction Commission (SUSPENDED - farmers keep 100%)
            'enable_transaction_commission': False,
            # Advertising & Free Tier
            'enable_ads': True,
            'free_tier_can_view_marketplace': True,
            'free_tier_can_view_prices': True,
            'free_tier_can_access_education': True,
        }
        
        for field, value in defaults.items():
            setattr(settings, field, value)
        
        settings.last_modified_by = request.user
        settings.notes = f"Reset to defaults by {request.user.username} on {settings.updated_at}"
        settings.save()
        
        serializer = PlatformSettingsSerializer(settings)
        return Response({
            'message': 'Platform settings reset to defaults',
            'settings': serializer.data
        })
