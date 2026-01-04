"""
Analytics URL Configuration

Provides URL patterns for YEA Admin analytics endpoints.
"""

from django.urls import path
from .analytics_views import (
    # YEA Admin Analytics
    AnalyticsOverviewView,
    AnalyticsDashboardView,
    AnalyticsProgramView,
    AnalyticsProductionView,
    AnalyticsMarketplaceView,
    AnalyticsAlertsView,
    
    # Platform Revenue (SUPER_ADMIN only)
    PlatformRevenueOverviewView,
    PlatformRevenueTrendView,
    PlatformAdvertisingView,
    PlatformPartnerPaymentsView,
    PlatformActivationStatsView,
    
    # Geographic Breakdown
    GeographicBreakdownView,
    MortalityBreakdownView,
    ProductionComparisonView,
    FarmRankingView,
    GeographicHierarchyView,
    
    # Egg Production Analytics
    EggProductionOverviewView,
    EggProductionTrendView,
    EggQualityAnalysisView,
    EggProductionByFarmView,
    EggProductionEfficiencyView,
    EggDefectAnalysisView,
    EggProductionComparisonView,
)

app_name = 'analytics'

urlpatterns = [
    # ==========================================================================
    # YEA ADMIN ANALYTICS - All YEA administrators
    # ==========================================================================
    
    # Full dashboard (all data in one call)
    path('', AnalyticsDashboardView.as_view(), name='dashboard'),
    
    # Overview cards only (quick load)
    path('overview/', AnalyticsOverviewView.as_view(), name='overview'),
    
    # Program metrics (applications, enrollments, registrations)
    path('program/', AnalyticsProgramView.as_view(), name='program'),
    
    # Production monitoring (eggs, mortality, performance)
    path('production/', AnalyticsProductionView.as_view(), name='production'),
    
    # Marketplace activity (transactions, NOT platform revenue)
    path('marketplace/', AnalyticsMarketplaceView.as_view(), name='marketplace'),
    
    # Alerts and watchlist
    path('alerts/', AnalyticsAlertsView.as_view(), name='alerts'),
    
    # ==========================================================================
    # PLATFORM REVENUE - SUPER_ADMIN and YEA_OFFICIAL only
    # ==========================================================================
    
    # Revenue overview
    path('platform-revenue/', PlatformRevenueOverviewView.as_view(), name='platform-revenue'),
    
    # Revenue trend
    path('platform-revenue/trend/', PlatformRevenueTrendView.as_view(), name='platform-revenue-trend'),
    
    # Advertising performance
    path('platform-revenue/advertising/', PlatformAdvertisingView.as_view(), name='platform-advertising'),
    
    # Partner payments
    path('platform-revenue/partner-payments/', PlatformPartnerPaymentsView.as_view(), name='partner-payments'),
    
    # Marketplace activation stats
    path('platform-revenue/activation/', PlatformActivationStatsView.as_view(), name='activation-stats'),
    
    # ==========================================================================
    # GEOGRAPHIC BREAKDOWN - Drill-down analytics by region/district/constituency
    # ==========================================================================
    
    # Comprehensive breakdown (farms, production, mortality by geographic level)
    path('geographic/breakdown/', GeographicBreakdownView.as_view(), name='geographic-breakdown'),
    
    # Mortality-specific breakdown with trends and risk levels
    path('geographic/mortality/', MortalityBreakdownView.as_view(), name='geographic-mortality'),
    
    # Production comparison with rankings
    path('geographic/comparison/', ProductionComparisonView.as_view(), name='geographic-comparison'),
    
    # Individual farm rankings with geographic filtering
    path('geographic/farms/', FarmRankingView.as_view(), name='farm-ranking'),
    
    # Geographic hierarchy for drill-down navigation
    path('geographic/hierarchy/', GeographicHierarchyView.as_view(), name='geographic-hierarchy'),
    
    # ==========================================================================
    # EGG PRODUCTION ANALYTICS - Comprehensive egg production analysis
    # ==========================================================================
    
    # Egg production overview with quality breakdown
    path('eggs/overview/', EggProductionOverviewView.as_view(), name='eggs-overview'),
    
    # Egg production trend over time
    path('eggs/trend/', EggProductionTrendView.as_view(), name='eggs-trend'),
    
    # Egg quality analysis by geographic level
    path('eggs/quality/', EggQualityAnalysisView.as_view(), name='eggs-quality'),
    
    # Individual farm egg production rankings
    path('eggs/farms/', EggProductionByFarmView.as_view(), name='eggs-farms'),
    
    # Egg production efficiency metrics
    path('eggs/efficiency/', EggProductionEfficiencyView.as_view(), name='eggs-efficiency'),
    
    # Egg defect analysis with recommendations
    path('eggs/defects/', EggDefectAnalysisView.as_view(), name='eggs-defects'),
    
    # Period comparison for egg production
    path('eggs/comparison/', EggProductionComparisonView.as_view(), name='eggs-comparison'),
]
