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
]
