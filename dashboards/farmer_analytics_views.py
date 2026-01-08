"""
Farmer Analytics Views

API endpoints for individual farmer analytics.

Endpoints:
- GET /api/analytics/farmer/ - Full analytics dashboard
- GET /api/analytics/farmer/production/ - Production analytics
- GET /api/analytics/farmer/flock-health/ - Flock health & mortality
- GET /api/analytics/farmer/financial/ - Financial analytics
- GET /api/analytics/farmer/feed/ - Feed efficiency
- GET /api/analytics/farmer/marketplace/ - Marketplace performance
- GET /api/analytics/farmer/inventory/ - Inventory status
- GET /api/analytics/farmer/benchmarks/ - Comparative benchmarks
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .services.farmer_analytics import FarmerAnalyticsService
from .farmer_analytics_serializers import (
    AnalyticsPeriodSerializer,
    FarmerAnalyticsSerializer,
    ProductionAnalyticsSerializer,
    FlockHealthAnalyticsSerializer,
    FinancialAnalyticsSerializer,
    FeedAnalyticsSerializer,
    MarketplaceAnalyticsSerializer,
    InventoryAnalyticsSerializer,
    BenchmarkAnalyticsSerializer,
)

logger = logging.getLogger(__name__)


class BaseFarmerAnalyticsView(APIView):
    """Base class for farmer analytics views"""
    permission_classes = [IsAuthenticated]
    
    def get_service(self, request):
        """Get analytics service for the authenticated user"""
        return FarmerAnalyticsService(request.user)
    
    def get_days(self, request, default=30):
        """Get days parameter from query string"""
        serializer = AnalyticsPeriodSerializer(data=request.query_params)
        if serializer.is_valid():
            return serializer.validated_data.get('days', default)
        return default


class FarmerAnalyticsDashboardView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/
    
    Get complete analytics dashboard for the authenticated farmer.
    
    Query Parameters:
        days (int): Number of days for analytics period (default: 30, max: 365)
    
    Returns:
        Complete analytics data covering:
        - Farm summary
        - Production analytics
        - Flock health & mortality
        - Financial analytics
        - Feed efficiency
        - Marketplace performance
        - Inventory status
        - Comparative benchmarks
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request)
        
        analytics = service.get_full_analytics(days=days)
        
        if 'error' in analytics:
            status_code = status.HTTP_404_NOT_FOUND if analytics.get('code') == 'NO_FARM' else status.HTTP_400_BAD_REQUEST
            return Response(analytics, status=status_code)
        
        return Response(analytics)


class ProductionAnalyticsView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/production/
    
    Get egg production analytics with trends.
    
    Query Parameters:
        days (int): Number of days for analytics period (default: 30)
    
    Returns:
        - Total eggs collected
        - Production rate (eggs per bird)
        - Daily/weekly trends
        - Quality breakdown (good vs broken/dirty)
        - Peak production days
        - Production forecasts
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        analytics = service.get_production_analytics(days=days)
        analytics['period_days'] = days
        return Response(analytics)


class FlockHealthAnalyticsView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/flock-health/
    
    Get flock health and mortality analytics.
    
    Query Parameters:
        days (int): Number of days for analytics period (default: 30)
    
    Returns:
        - Mortality rates
        - Deaths by cause
        - Survival rates
        - Flock-level details
        - Health alerts
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        analytics = service.get_flock_health_analytics(days=days)
        analytics['period_days'] = days
        return Response(analytics)


class FinancialAnalyticsView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/financial/
    
    Get financial analytics including revenue, expenses, and profit.
    
    Query Parameters:
        days (int): Number of days for analytics period (default: 90)
    
    Returns:
        - Revenue from eggs, birds, marketplace
        - Expenses (feed, medication)
        - Profit margins
        - Revenue trends
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request, default=90)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        analytics = service.get_financial_analytics(days=days)
        analytics['period_days'] = days
        return Response(analytics)


class FeedAnalyticsView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/feed/
    
    Get feed consumption and efficiency analytics.
    
    Query Parameters:
        days (int): Number of days for analytics period (default: 30)
    
    Returns:
        - Feed consumption trends
        - Feed conversion ratio (FCR)
        - Cost per egg/bird
        - Current stock levels
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        analytics = service.get_feed_analytics(days=days)
        analytics['period_days'] = days
        return Response(analytics)


class MarketplaceAnalyticsView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/marketplace/
    
    Get marketplace performance analytics.
    
    Query Parameters:
        days (int): Number of days for analytics period (default: 30)
    
    Returns:
        - Order counts and values
        - Customer metrics
        - Product performance
        - Daily trends
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        analytics = service.get_marketplace_analytics(days=days)
        analytics['period_days'] = days
        return Response(analytics)


class InventoryAnalyticsView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/inventory/
    
    Get current inventory status.
    
    Returns:
        - Stock levels by category
        - Stock value
        - Movement summary
        - Low stock alerts
    """
    
    def get(self, request):
        service = self.get_service(request)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        analytics = service.get_inventory_analytics()
        return Response(analytics)


class BenchmarkAnalyticsView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/benchmarks/
    
    Get comparative benchmarks.
    
    Query Parameters:
        days (int): Number of days for analytics period (default: 30)
    
    Returns:
        - Performance vs last period
        - Performance vs regional average
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        analytics = service.get_benchmark_analytics(days=days)
        analytics['period_days'] = days
        return Response(analytics)


class FarmerAnalyticsSummaryView(BaseFarmerAnalyticsView):
    """
    GET /api/analytics/farmer/summary/
    
    Get a lightweight summary for dashboard cards.
    Quick metrics without detailed breakdowns.
    """
    
    def get(self, request):
        service = self.get_service(request)
        days = self.get_days(request, default=30)
        
        if not service.farm:
            return Response({
                'error': 'No farm found for this user',
                'code': 'NO_FARM'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get lightweight data
        production = service.get_production_analytics(days=days)
        health = service.get_flock_health_analytics(days=days)
        financial = service.get_financial_analytics(days=days)
        marketplace = service.get_marketplace_analytics(days=days)
        
        summary = {
            'period_days': days,
            'farm': service._get_farm_summary(),
            'quick_stats': {
                'total_eggs': production.get('summary', {}).get('total_eggs', 0),
                'avg_daily_eggs': production.get('summary', {}).get('avg_daily_production', 0),
                'production_rate': production.get('summary', {}).get('production_rate_percent', 0),
                'current_birds': health.get('summary', {}).get('current_bird_count', 0),
                'mortality_rate': health.get('summary', {}).get('mortality_rate_period', 0),
                'total_revenue': financial.get('summary', {}).get('total_revenue', 0),
                'profit_margin': financial.get('summary', {}).get('profit_margin_percent', 0),
                'marketplace_orders': marketplace.get('summary', {}).get('completed_orders', 0) if marketplace.get('enabled') else 0,
            },
            'alerts': health.get('alerts', []),
        }
        
        return Response(summary)
