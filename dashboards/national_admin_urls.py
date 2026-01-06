"""
National Admin / Minister Reports URL Configuration

API endpoints for National Administrator and Agriculture Minister reporting.
Supports geographic drill-down: National → Regional → Constituency → Farm

Base URL: /api/admin/reports/
"""

from django.urls import path

from .national_admin_views import (
    # Executive Dashboard
    ExecutiveDashboardView,
    
    # Program Performance
    ProgramPerformanceView,
    EnrollmentTrendView,
    
    # Production
    ProductionOverviewView,
    RegionalProductionComparisonView,
    
    # Financial
    FinancialOverviewView,
    
    # Flock Health
    FlockHealthOverviewView,
    
    # Food Security
    FoodSecurityMetricsView,
    
    # Procurement
    ProcurementOverviewView,
    
    # Farmer Welfare
    FarmerWelfareMetricsView,
    
    # Operational
    OperationalMetricsView,
    
    # Drill-down Navigation
    DrillDownOptionsView,
    FarmListView,
    
    # Async Operations
    GenerateReportAsyncView,
    RefreshCacheView,
)

from .national_admin_exports import (
    ExportExecutiveReportExcelView,
    ExportExecutiveReportPDFView,
    ExportReportCSVView,
)

app_name = 'national_admin_reports'

urlpatterns = [
    # =========================================================================
    # EXECUTIVE DASHBOARD (Main Landing)
    # =========================================================================
    
    # Combined executive dashboard
    path(
        'executive/',
        ExecutiveDashboardView.as_view(),
        name='executive-dashboard'
    ),
    
    # =========================================================================
    # PROGRAM PERFORMANCE
    # =========================================================================
    
    # Program performance overview
    path(
        'program-performance/',
        ProgramPerformanceView.as_view(),
        name='program-performance'
    ),
    
    # Enrollment trend over time
    path(
        'enrollment-trend/',
        EnrollmentTrendView.as_view(),
        name='enrollment-trend'
    ),
    
    # =========================================================================
    # PRODUCTION
    # =========================================================================
    
    # Production overview
    path(
        'production/',
        ProductionOverviewView.as_view(),
        name='production-overview'
    ),
    
    # Regional production comparison (national view only)
    path(
        'production/regional-comparison/',
        RegionalProductionComparisonView.as_view(),
        name='regional-production-comparison'
    ),
    
    # =========================================================================
    # FINANCIAL
    # =========================================================================
    
    # Financial and economic impact
    path(
        'financial/',
        FinancialOverviewView.as_view(),
        name='financial-overview'
    ),
    
    # =========================================================================
    # FLOCK HEALTH
    # =========================================================================
    
    # Flock health and biosecurity
    path(
        'flock-health/',
        FlockHealthOverviewView.as_view(),
        name='flock-health'
    ),
    
    # =========================================================================
    # FOOD SECURITY
    # =========================================================================
    
    # Food security metrics
    path(
        'food-security/',
        FoodSecurityMetricsView.as_view(),
        name='food-security'
    ),
    
    # =========================================================================
    # PROCUREMENT
    # =========================================================================
    
    # Government/institutional procurement
    path(
        'procurement/',
        ProcurementOverviewView.as_view(),
        name='procurement'
    ),
    
    # =========================================================================
    # FARMER WELFARE
    # =========================================================================
    
    # Farmer welfare and impact
    path(
        'farmer-welfare/',
        FarmerWelfareMetricsView.as_view(),
        name='farmer-welfare'
    ),
    
    # =========================================================================
    # OPERATIONAL
    # =========================================================================
    
    # Operational efficiency
    path(
        'operational/',
        OperationalMetricsView.as_view(),
        name='operational'
    ),
    
    # =========================================================================
    # DRILL-DOWN NAVIGATION
    # =========================================================================
    
    # Get available drill-down options
    path(
        'drill-down/',
        DrillDownOptionsView.as_view(),
        name='drill-down-options'
    ),
    
    # Get farms list (deepest drill-down level)
    path(
        'farms/',
        FarmListView.as_view(),
        name='farms-list'
    ),
    
    # =========================================================================
    # ASYNC OPERATIONS
    # =========================================================================
    
    # Trigger async report generation
    path(
        'generate/',
        GenerateReportAsyncView.as_view(),
        name='generate-report'
    ),
    
    # Refresh cached reports (Super Admin)
    path(
        'refresh-cache/',
        RefreshCacheView.as_view(),
        name='refresh-cache'
    ),
    
    # =========================================================================
    # EXPORT (DOWNLOADABLE REPORTS)
    # =========================================================================
    
    # Export executive report as Excel
    path(
        'export/excel/executive/',
        ExportExecutiveReportExcelView.as_view(),
        name='export-excel-executive'
    ),
    
    # Export executive report as PDF
    path(
        'export/pdf/executive/',
        ExportExecutiveReportPDFView.as_view(),
        name='export-pdf-executive'
    ),
    
    # Export specific report as CSV
    path(
        'export/csv/<str:report_type>/',
        ExportReportCSVView.as_view(),
        name='export-csv'
    ),
]
