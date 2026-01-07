"""
Farmer Analytics URL Routes

API endpoints for individual farmer analytics.
All endpoints require authentication and return data scoped to the farmer's farm.
"""

from django.urls import path
from .farmer_analytics_views import (
    FarmerAnalyticsDashboardView,
    FarmerAnalyticsSummaryView,
    ProductionAnalyticsView,
    FlockHealthAnalyticsView,
    FinancialAnalyticsView,
    FeedAnalyticsView,
    MarketplaceAnalyticsView,
    InventoryAnalyticsView,
    BenchmarkAnalyticsView,
)
from .farmer_analytics_exports import (
    ExportAnalyticsExcelView,
    ExportAnalyticsPDFView,
    ExportAnalyticsCSVView,
)

app_name = 'farmer_analytics'

urlpatterns = [
    # Full dashboard (all analytics combined)
    path('', FarmerAnalyticsDashboardView.as_view(), name='dashboard'),
    path('overview/', FarmerAnalyticsDashboardView.as_view(), name='overview'),  # Alias for tests
    
    # Lightweight summary for dashboard cards
    path('summary/', FarmerAnalyticsSummaryView.as_view(), name='summary'),
    
    # Individual analytics sections
    path('production/', ProductionAnalyticsView.as_view(), name='production'),
    path('flock-health/', FlockHealthAnalyticsView.as_view(), name='flock-health'),
    path('financial/', FinancialAnalyticsView.as_view(), name='financial'),
    path('feed/', FeedAnalyticsView.as_view(), name='feed'),
    path('marketplace/', MarketplaceAnalyticsView.as_view(), name='marketplace'),
    path('inventory/', InventoryAnalyticsView.as_view(), name='inventory'),
    path('benchmarks/', BenchmarkAnalyticsView.as_view(), name='benchmarks'),
    
    # Export endpoints
    path('export/excel/', ExportAnalyticsExcelView.as_view(), name='export-excel'),
    path('export/pdf/', ExportAnalyticsPDFView.as_view(), name='export-pdf'),
    path('export/csv/', ExportAnalyticsCSVView.as_view(), name='export-csv'),
]
