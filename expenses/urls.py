"""
URL configuration for Expense Tracking app.

All endpoints are prefixed with /api/expenses/
"""

from django.urls import path
from .views import (
    # Categories
    ExpenseCategoryListView,
    ExpenseFrequencyListView,
    
    # Sub-categories
    ExpenseSubCategoryListCreateView,
    ExpenseSubCategoryDetailView,
    
    # Expenses
    ExpenseListCreateView,
    ExpenseDetailView,
    BulkExpenseCreateView,
    
    # Labor
    LaborRecordListCreateView,
    LaborRecordDetailView,
    LaborRecordPayView,
    BulkLaborRecordCreateView,
    
    # Utilities
    UtilityRecordListCreateView,
    UtilityRecordDetailView,
    UtilityRecordPayView,
    
    # Mortality Loss
    MortalityLossRecordListCreateView,
    MortalityLossRecordDetailView,
    MortalityLossPreviewView,
    FlockInvestmentSummaryView,
    
    # Recurring
    RecurringExpenseTemplateListCreateView,
    RecurringExpenseTemplateDetailView,
    GenerateRecurringExpenseView,
    
    # Summaries
    ExpenseSummaryListView,
    
    # Dashboard & Analytics
    ExpenseDashboardView,
    ExpenseAnalyticsView,
    FlockCostBreakdownView,
)

app_name = 'expenses'

urlpatterns = [
    # ==========================================================================
    # CATEGORIES (Constants)
    # ==========================================================================
    path('categories/', ExpenseCategoryListView.as_view(), name='category-list'),
    path('frequencies/', ExpenseFrequencyListView.as_view(), name='frequency-list'),
    
    # ==========================================================================
    # SUB-CATEGORIES (Custom)
    # ==========================================================================
    path('sub-categories/', ExpenseSubCategoryListCreateView.as_view(), name='subcategory-list'),
    path('sub-categories/<uuid:pk>/', ExpenseSubCategoryDetailView.as_view(), name='subcategory-detail'),
    
    # ==========================================================================
    # EXPENSES
    # ==========================================================================
    path('', ExpenseListCreateView.as_view(), name='expense-list'),
    path('<uuid:pk>/', ExpenseDetailView.as_view(), name='expense-detail'),
    path('bulk/', BulkExpenseCreateView.as_view(), name='expense-bulk-create'),
    
    # ==========================================================================
    # LABOR RECORDS
    # ==========================================================================
    path('labor/', LaborRecordListCreateView.as_view(), name='labor-list'),
    path('labor/<uuid:pk>/', LaborRecordDetailView.as_view(), name='labor-detail'),
    path('labor/<uuid:pk>/pay/', LaborRecordPayView.as_view(), name='labor-pay'),
    path('labor/bulk/', BulkLaborRecordCreateView.as_view(), name='labor-bulk-create'),
    
    # ==========================================================================
    # UTILITY RECORDS
    # ==========================================================================
    path('utilities/', UtilityRecordListCreateView.as_view(), name='utility-list'),
    path('utilities/<uuid:pk>/', UtilityRecordDetailView.as_view(), name='utility-detail'),
    path('utilities/<uuid:pk>/pay/', UtilityRecordPayView.as_view(), name='utility-pay'),
    
    # ==========================================================================
    # MORTALITY LOSS RECORDS
    # ==========================================================================
    path('mortality-losses/', MortalityLossRecordListCreateView.as_view(), name='mortality-loss-list'),
    path('mortality-loss/', MortalityLossRecordListCreateView.as_view(), name='mortality-loss-list-alt'),  # Alias
    path('mortality-losses/<uuid:pk>/', MortalityLossRecordDetailView.as_view(), name='mortality-loss-detail'),
    path('mortality-loss/<uuid:pk>/', MortalityLossRecordDetailView.as_view(), name='mortality-loss-detail-alt'),  # Alias
    path('mortality-loss/preview/', MortalityLossPreviewView.as_view(), name='mortality-loss-preview'),
    
    # ==========================================================================
    # FLOCK INVESTMENT
    # ==========================================================================
    path('flock/<uuid:flock_id>/investment/', FlockInvestmentSummaryView.as_view(), name='flock-investment'),
    
    # ==========================================================================
    # RECURRING EXPENSE TEMPLATES
    # ==========================================================================
    path('recurring/', RecurringExpenseTemplateListCreateView.as_view(), name='recurring-list'),
    path('recurring/<uuid:pk>/', RecurringExpenseTemplateDetailView.as_view(), name='recurring-detail'),
    path('recurring/<uuid:pk>/generate/', GenerateRecurringExpenseView.as_view(), name='recurring-generate'),
    
    # ==========================================================================
    # SUMMARIES
    # ==========================================================================
    path('summary/', ExpenseSummaryListView.as_view(), name='summary-list'),
    
    # ==========================================================================
    # DASHBOARD & ANALYTICS
    # ==========================================================================
    path('dashboard/', ExpenseDashboardView.as_view(), name='dashboard'),
    path('analytics/', ExpenseAnalyticsView.as_view(), name='analytics'),
    path('flock/<uuid:flock_id>/costs/', FlockCostBreakdownView.as_view(), name='flock-costs'),
]
