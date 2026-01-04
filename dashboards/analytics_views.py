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


# =============================================================================
# GEOGRAPHIC BREAKDOWN ENDPOINTS
# =============================================================================

class GeographicBreakdownView(APIView):
    """
    GET /api/admin/analytics/geographic/breakdown/
    
    Comprehensive geographic breakdown of all metrics.
    
    Query params:
        - level: 'region', 'district', or 'constituency' (default: 'region')
        - parent: Parent filter for drill-down (e.g., region name when level='district')
        - days: Period for production data (default: 30)
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        level = request.query_params.get('level', 'region')
        parent_filter = request.query_params.get('parent')
        days = int(request.query_params.get('days', 30))
        
        if level not in ['region', 'district', 'constituency']:
            return Response(
                {'error': 'Invalid level. Use region, district, or constituency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = service.get_geographic_breakdown(
            level=level,
            parent_filter=parent_filter,
            period_days=days
        )
        
        return Response(data, status=status.HTTP_200_OK)


class MortalityBreakdownView(APIView):
    """
    GET /api/admin/analytics/geographic/mortality/
    
    Detailed mortality breakdown by geographic level with trends.
    
    Query params:
        - level: 'region', 'district', or 'constituency' (default: 'region')
        - parent: Parent filter for drill-down
        - days: Current period days (default: 30)
        - comparison_days: Previous period for comparison (default: 30)
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        level = request.query_params.get('level', 'region')
        parent_filter = request.query_params.get('parent')
        days = int(request.query_params.get('days', 30))
        comparison_days = int(request.query_params.get('comparison_days', 30))
        
        if level not in ['region', 'district', 'constituency']:
            return Response(
                {'error': 'Invalid level. Use region, district, or constituency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = service.get_mortality_breakdown(
            level=level,
            parent_filter=parent_filter,
            period_days=days,
            comparison_period_days=comparison_days
        )
        
        return Response(data, status=status.HTTP_200_OK)


class ProductionComparisonView(APIView):
    """
    GET /api/admin/analytics/geographic/comparison/
    
    Production comparison across geographic units with rankings.
    
    Query params:
        - level: 'region', 'district', or 'constituency' (default: 'region')
        - parent: Parent filter for drill-down
        - days: Period for data (default: 30)
        - metric: 'eggs', 'mortality', 'production_rate', 'birds', 'farms' (default: 'eggs')
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        level = request.query_params.get('level', 'region')
        parent_filter = request.query_params.get('parent')
        days = int(request.query_params.get('days', 30))
        metric = request.query_params.get('metric', 'eggs')
        
        if level not in ['region', 'district', 'constituency']:
            return Response(
                {'error': 'Invalid level. Use region, district, or constituency'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if metric not in ['eggs', 'mortality', 'production_rate', 'birds', 'farms']:
            return Response(
                {'error': 'Invalid metric. Use eggs, mortality, production_rate, birds, or farms'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = service.get_production_comparison(
            level=level,
            parent_filter=parent_filter,
            period_days=days,
            metric=metric
        )
        
        return Response(data, status=status.HTTP_200_OK)


class FarmRankingView(APIView):
    """
    GET /api/admin/analytics/geographic/farms/
    
    Individual farm performance rankings with geographic filtering.
    
    Query params:
        - region: Filter by region
        - district: Filter by district
        - constituency: Filter by constituency
        - metric: Ranking metric ('eggs', 'production_rate', 'mortality', 'birds')
        - days: Period for data (default: 30)
        - limit: Max farms to return (default: 50)
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        
        region = request.query_params.get('region')
        district = request.query_params.get('district')
        constituency = request.query_params.get('constituency')
        metric = request.query_params.get('metric', 'eggs')
        days = int(request.query_params.get('days', 30))
        limit = int(request.query_params.get('limit', 50))
        
        if metric not in ['eggs', 'production_rate', 'mortality', 'birds']:
            return Response(
                {'error': 'Invalid metric. Use eggs, production_rate, mortality, or birds'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        data = service.get_farm_performance_ranking(
            region=region,
            district=district,
            constituency=constituency,
            metric=metric,
            period_days=days,
            limit=limit
        )
        
        return Response(data, status=status.HTTP_200_OK)


class GeographicHierarchyView(APIView):
    """
    GET /api/admin/analytics/geographic/hierarchy/
    
    Get available geographic hierarchy for drill-down navigation.
    Returns regions -> districts -> constituencies structure.
    """
    permission_classes = [IsYEAAdmin]
    
    def get(self, request):
        service = YEAAnalyticsService(user=request.user)
        data = service.get_geographic_hierarchy()
        return Response(data, status=status.HTTP_200_OK)
