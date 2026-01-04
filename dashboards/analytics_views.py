"""
YEA Admin Analytics Views

Provides REST API endpoints for YEA administrator analytics.
Geographic filtering is automatically applied based on user role.

Access Control:
- /api/admin/analytics/* - YEA Admins (National, Regional, Constituency)
- /api/admin/analytics/platform-revenue/* - SUPER_ADMIN only
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from accounts.policies import UserPolicy
from .services.yea_analytics import YEAAnalyticsService
from .services.platform_revenue import PlatformRevenueService


class IsYEAAdmin(IsAuthenticated):
    """
    Permission check for YEA administrators.
    Allows: SUPER_ADMIN, YEA_OFFICIAL, NATIONAL_ADMIN, REGIONAL_COORDINATOR, CONSTITUENCY_OFFICIAL
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        user = request.user
        return user.role in [
            'SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN',
            'REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL'
        ]


class IsPlatformOwner(IsAuthenticated):
    """
    Permission check for platform owner (revenue access).
    Allows: SUPER_ADMIN, YEA_OFFICIAL only
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        return request.user.role in ['SUPER_ADMIN', 'YEA_OFFICIAL']


# =============================================================================
# YEA ADMIN ANALYTICS ENDPOINTS
# =============================================================================

class AnalyticsOverviewView(APIView):
    """
    GET /api/admin/analytics/overview/
    
    Executive overview with key metrics cards.
    Geographically filtered based on user role.
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        data = service.get_executive_overview()
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsDashboardView(APIView):
    """
    GET /api/admin/analytics/
    
    Full analytics dashboard data in one call.
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        data = {
            'overview': service.get_executive_overview(),
            'application_pipeline': service.get_application_pipeline(),
            'production': service.get_production_overview(),
            'marketplace': service.get_marketplace_activity(),
            'alerts': service.get_alerts()
        }
        
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsProgramView(APIView):
    """
    GET /api/admin/analytics/program/
    
    Program-specific metrics: applications, enrollments, registrations.
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        months = int(request.query_params.get('months', 6))
        
        data = {
            'application_pipeline': service.get_application_pipeline(),
            'registration_trend': service.get_registration_trend(months=months),
            'farms_by_region': service.get_farms_by_region(),
            'batch_enrollment': service.get_batch_enrollment_stats()
        }
        
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsProductionView(APIView):
    """
    GET /api/admin/analytics/production/
    
    Production monitoring: eggs, mortality, performance.
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 10))
        
        data = {
            'overview': service.get_production_overview(),
            'trend': service.get_production_trend(days=days),
            'by_region': service.get_production_by_region(),
            'top_farms': service.get_top_performing_farms(limit=limit),
            'underperforming': service.get_underperforming_farms(limit=limit)
        }
        
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsMarketplaceView(APIView):
    """
    GET /api/admin/analytics/marketplace/
    
    Marketplace activity: transactions, sales volume (NOT platform revenue).
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        limit = int(request.query_params.get('limit', 10))
        
        data = {
            'activity': service.get_marketplace_activity(),
            'sales_by_region': service.get_sales_by_region(),
            'top_sellers': service.get_top_selling_farmers(limit=limit)
        }
        
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsAlertsView(APIView):
    """
    GET /api/admin/analytics/alerts/
    
    System alerts and watchlist for admin attention.
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        limit = int(request.query_params.get('limit', 20))
        
        data = {
            'alerts': service.get_alerts(),
            'watchlist': service.get_watchlist(limit=limit)
        }
        
        return Response(data, status=status.HTTP_200_OK)


# =============================================================================
# PLATFORM REVENUE ENDPOINTS (SUPER_ADMIN ONLY)
# =============================================================================

class PlatformRevenueOverviewView(APIView):
    """
    GET /api/admin/analytics/platform-revenue/
    
    Platform revenue overview (advertising + marketplace activation fees).
    SUPER_ADMIN and YEA_OFFICIAL only.
    """
    permission_classes = [IsPlatformOwner]
    
    def get(self, request):
        service = PlatformRevenueService()
        data = service.get_revenue_overview()
        return Response(data, status=status.HTTP_200_OK)


class PlatformRevenueTrendView(APIView):
    """
    GET /api/admin/analytics/platform-revenue/trend/
    
    Monthly revenue trend.
    """
    permission_classes = [IsPlatformOwner]
    
    def get(self, request):
        service = PlatformRevenueService()
        
        months = int(request.query_params.get('months', 6))
        data = service.get_revenue_trend(months=months)
        
        return Response(data, status=status.HTTP_200_OK)


class PlatformAdvertisingView(APIView):
    """
    GET /api/admin/analytics/platform-revenue/advertising/
    
    Advertising performance metrics.
    """
    permission_classes = [IsPlatformOwner]
    
    def get(self, request):
        service = PlatformRevenueService()
        data = service.get_advertising_performance()
        return Response(data, status=status.HTTP_200_OK)


class PlatformPartnerPaymentsView(APIView):
    """
    GET /api/admin/analytics/platform-revenue/partner-payments/
    
    Partner payment tracking.
    """
    permission_classes = [IsPlatformOwner]
    
    def get(self, request):
        service = PlatformRevenueService()
        
        payment_status = request.query_params.get('status')
        data = service.get_partner_payments(status=payment_status)
        
        return Response(data, status=status.HTTP_200_OK)


class PlatformActivationStatsView(APIView):
    """
    GET /api/admin/analytics/platform-revenue/activation/
    
    Marketplace activation (subscription) statistics.
    """
    permission_classes = [IsPlatformOwner]
    
    def get(self, request):
        service = PlatformRevenueService()
        data = service.get_marketplace_activation_stats()
        return Response(data, status=status.HTTP_200_OK)
