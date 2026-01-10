"""
National Admin / Agriculture Minister Analytics Views

API endpoints for National Administrator and Agriculture Minister reporting.
Supports geographic drill-down: National → Regional → Constituency → Farm

Performance Features:
- Redis caching with configurable TTL
- Pre-computed reports via Celery
- Async report generation for heavy operations
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.core.cache import cache
from django.utils import timezone
import logging

from .services.national_admin_analytics import NationalAdminAnalyticsService
from .national_admin_serializers import (
    ExecutiveDashboardSerializer,
    ProgramPerformanceSerializer,
    EnrollmentTrendSerializer,
    ProductionOverviewSerializer,
    RegionalProductionComparisonSerializer,
    FinancialOverviewSerializer,
    FlockHealthOverviewSerializer,
    FoodSecurityMetricsSerializer,
    ProcurementOverviewSerializer,
    FarmerWelfareMetricsSerializer,
    OperationalMetricsSerializer,
    DrillDownOptionsSerializer,
    FarmListResponseSerializer,
    ReportRequestSerializer,
    FarmListRequestSerializer,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PERMISSION CLASSES
# =============================================================================

class IsNationalAdminOrAbove:
    """
    Permission class for National Admin/Minister level access.
    
    Allowed roles:
    - SUPER_ADMIN
    - NATIONAL_ADMIN
    - REGIONAL_COORDINATOR (filtered to their region)
    - CONSTITUENCY_OFFICIAL (filtered to their constituency)
    """
    
    ALLOWED_ROLES = [
        'SUPER_ADMIN',
        'NATIONAL_ADMIN',
        'REGIONAL_COORDINATOR',
        'CONSTITUENCY_OFFICIAL',
    ]
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in self.ALLOWED_ROLES


class NationalAdminPermission(IsAuthenticated):
    """Combined permission check for authenticated admin users."""
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        admin_checker = IsNationalAdminOrAbove()
        return admin_checker.has_permission(request, view)


# =============================================================================
# BASE VIEW
# =============================================================================

class BaseNationalAdminView(APIView):
    """Base view with common functionality for National Admin endpoints."""
    
    permission_classes = [NationalAdminPermission]
    
    def get_service(self, request, use_cache: bool = True):
        """Get analytics service with user context."""
        return NationalAdminAnalyticsService(
            user=request.user,
            use_cache=use_cache
        )
    
    def get_scope_params(self, request):
        """Extract region/constituency scope from request."""
        requested_region = request.query_params.get('region')
        requested_constituency = request.query_params.get('constituency')
        
        # Validate and enforce geographic scoping
        if request.user.role == 'REGIONAL_COORDINATOR':
            # Regional coordinators can only access their assigned region
            if requested_region and requested_region != request.user.region:
                raise PermissionDenied("Regional coordinators can only access their assigned region")
            region = request.user.region
            constituency = None
        elif request.user.role == 'CONSTITUENCY_OFFICIAL':
            # Constituency officials can only access their assigned constituency
            if requested_constituency and requested_constituency != request.user.constituency:
                raise PermissionDenied("Constituency officials can only access their assigned constituency")
            constituency = request.user.constituency
            region = requested_region  # Keep region for context
        else:
            # National-level users can access any region
            region = requested_region
            constituency = requested_constituency
        
        return region, constituency
    
    def get_cache_or_compute(self, cache_key: str, compute_func, ttl: int = 1800):
        """Try cache first, then compute if needed."""
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        result = compute_func()
        cache.set(cache_key, result, timeout=ttl)
        return result


# =============================================================================
# EXECUTIVE DASHBOARD (MAIN LANDING)
# =============================================================================

class ExecutiveDashboardView(BaseNationalAdminView):
    """
    GET /api/reports/executive/
    
    Main executive dashboard combining all key metrics.
    Optimized for the Minister/National Admin landing page.
    
    Query Parameters:
    - region: Filter by region
    - constituency: Filter by constituency
    
    Response includes drill-down navigation options.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        
        # Try pre-computed cache first
        cache_key = f'national_admin:executive_dashboard:{region or "national"}:{constituency or "all"}'
        
        def compute():
            service = self.get_service(request, use_cache=True)
            return service.get_executive_dashboard(region, constituency)
        
        data = self.get_cache_or_compute(cache_key, compute, ttl=300)  # 5 min
        
        return Response(data)


# =============================================================================
# PROGRAM PERFORMANCE
# =============================================================================

class ProgramPerformanceView(BaseNationalAdminView):
    """
    GET /api/reports/program-performance/
    
    Program performance metrics including enrollment, growth, retention.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        
        service = self.get_service(request)
        data = service.get_program_performance_overview(region, constituency)
        
        return Response(data)


class EnrollmentTrendView(BaseNationalAdminView):
    """
    GET /api/reports/enrollment-trend/
    
    Enrollment trend over time.
    
    Query Parameters:
    - months: Number of months to include (default: 12)
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        months = int(request.query_params.get('months', 12))
        months = min(max(months, 1), 36)  # Limit 1-36 months
        
        service = self.get_service(request)
        data = service.get_enrollment_trend(months, region, constituency)
        
        return Response(data)


# =============================================================================
# PRODUCTION
# =============================================================================

class ProductionOverviewView(BaseNationalAdminView):
    """
    GET /api/reports/production/
    
    Production overview with trends.
    
    Query Parameters:
    - days: Number of days to include (default: 30)
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        days = int(request.query_params.get('days', 30))
        days = min(max(days, 1), 365)  # Limit 1-365 days
        
        service = self.get_service(request)
        data = service.get_production_overview(region, constituency, days)
        
        return Response(data)


class RegionalProductionComparisonView(BaseNationalAdminView):
    """
    GET /api/reports/production/regional-comparison/
    
    Compare production across all regions.
    National-level view only (no filtering).
    """
    
    def get(self, request):
        # This is always national level
        if request.user.role in ['REGIONAL_COORDINATOR', 'CONSTITUENCY_OFFICIAL']:
            return Response(
                {'error': 'Regional comparison requires national-level access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        service = self.get_service(request)
        data = service.get_regional_production_comparison()
        
        return Response(data)


# =============================================================================
# FINANCIAL
# =============================================================================

class FinancialOverviewView(BaseNationalAdminView):
    """
    GET /api/reports/financial/
    
    Financial and economic impact metrics.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        days = int(request.query_params.get('days', 30))
        days = min(max(days, 1), 365)
        
        service = self.get_service(request)
        data = service.get_financial_overview(region, constituency, days)
        
        return Response(data)


# =============================================================================
# FLOCK HEALTH
# =============================================================================

class FlockHealthOverviewView(BaseNationalAdminView):
    """
    GET /api/reports/flock-health/
    
    Flock health and biosecurity metrics.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        days = int(request.query_params.get('days', 30))
        days = min(max(days, 1), 365)
        
        service = self.get_service(request)
        data = service.get_flock_health_overview(region, constituency, days)
        
        return Response(data)


# =============================================================================
# FOOD SECURITY
# =============================================================================

class FoodSecurityMetricsView(BaseNationalAdminView):
    """
    GET /api/reports/food-security/
    
    Food security and market contribution metrics.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        
        service = self.get_service(request)
        data = service.get_food_security_metrics(region, constituency)
        
        return Response(data)


# =============================================================================
# PROCUREMENT
# =============================================================================

class ProcurementOverviewView(BaseNationalAdminView):
    """
    GET /api/reports/procurement/
    
    Government/institutional procurement metrics.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        days = int(request.query_params.get('days', 90))
        days = min(max(days, 1), 365)
        
        service = self.get_service(request)
        data = service.get_procurement_overview(region, constituency, days)
        
        return Response(data)


# =============================================================================
# FARMER WELFARE
# =============================================================================

class FarmerWelfareMetricsView(BaseNationalAdminView):
    """
    GET /api/reports/farmer-welfare/
    
    Farmer welfare and social impact metrics.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        
        service = self.get_service(request)
        data = service.get_farmer_welfare_metrics(region, constituency)
        
        return Response(data)


# =============================================================================
# OPERATIONAL
# =============================================================================

class OperationalMetricsView(BaseNationalAdminView):
    """
    GET /api/reports/operational/
    
    Operational efficiency metrics.
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        
        service = self.get_service(request)
        data = service.get_operational_metrics(region, constituency)
        
        return Response(data)


# =============================================================================
# DRILL-DOWN NAVIGATION
# =============================================================================

class DrillDownOptionsView(BaseNationalAdminView):
    """
    GET /api/reports/drill-down/
    
    Get available drill-down options for navigation.
    
    Query Parameters:
    - region: Current region (to get constituencies)
    """
    
    def get(self, request):
        region = request.query_params.get('region')
        
        # Auto-scope for regional coordinators
        if request.user.role == 'REGIONAL_COORDINATOR':
            region = request.user.region
        
        service = self.get_service(request)
        data = service.get_drill_down_options(region)
        
        return Response(data)


class FarmListView(BaseNationalAdminView):
    """
    GET /api/reports/farms/
    
    Get list of farms for the deepest drill-down level.
    
    Query Parameters:
    - region: Filter by region
    - constituency: Filter by constituency  
    - page: Page number (default: 1)
    - page_size: Items per page (default: 20, max: 100)
    """
    
    def get(self, request):
        region, constituency = self.get_scope_params(request)
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        page_size = min(max(page_size, 1), 100)
        
        service = self.get_service(request)
        data = service.get_farms_in_scope(region, constituency, page, page_size)
        
        return Response(data)


# =============================================================================
# ASYNC REPORT GENERATION
# =============================================================================

class GenerateReportAsyncView(BaseNationalAdminView):
    """
    POST /api/reports/generate/
    
    Trigger async report generation for heavy operations.
    Returns a task ID for status checking.
    
    Request Body:
    - report_type: Type of report to generate
    - region: Optional region filter
    - constituency: Optional constituency filter
    """
    
    def post(self, request):
        from dashboards.tasks import generate_minister_report
        
        report_type = request.data.get('report_type')
        region = request.data.get('region')
        constituency = request.data.get('constituency')
        
        valid_types = [
            'executive_dashboard', 'program_performance', 'production',
            'financial', 'flock_health', 'food_security', 'procurement',
            'farmer_welfare', 'operational', 'regional_comparison',
            'enrollment_trend'
        ]
        
        if report_type not in valid_types:
            return Response(
                {
                    'error': f'Invalid report type. Valid types: {valid_types}',
                    'code': 'INVALID_REPORT_TYPE'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Dispatch async task
        task = generate_minister_report.delay(
            report_type=report_type,
            region=region,
            constituency=constituency
        )
        
        return Response({
            'task_id': task.id,
            'status': 'queued',
            'report_type': report_type,
            'message': 'Report generation started. Check status with task_id.',
        }, status=status.HTTP_202_ACCEPTED)


class RefreshCacheView(BaseNationalAdminView):
    """
    POST /api/reports/refresh-cache/
    
    Manually refresh cached reports.
    Super Admin only.
    
    Request Body:
    - report_types: List of report types to refresh (optional, all if empty)
    - region: Region to refresh (optional)
    """
    
    def post(self, request):
        if request.user.role not in ['SUPER_ADMIN', 'NATIONAL_ADMIN']:
            return Response(
                {'error': 'Cache refresh requires admin access'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from dashboards.tasks import refresh_national_admin_cache
        
        report_types = request.data.get('report_types', [])
        region = request.data.get('region')
        
        task = refresh_national_admin_cache.delay(report_types, region)
        
        return Response({
            'task_id': task.id,
            'status': 'queued',
            'message': 'Cache refresh started.',
        }, status=status.HTTP_202_ACCEPTED)
