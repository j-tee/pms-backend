"""
Dashboard URL Configuration
"""

from django.urls import path
from .views import (
    # Executive Dashboard
    ExecutiveDashboardView,
    ExecutiveOverviewView,
    ExecutiveChartsView,
    
    # Officer Dashboard
    OfficerDashboardView,
    OfficerOverviewView,
    OfficerOrdersView,
    OfficerOrderTimelineView,
    
    # Farmer Dashboard
    FarmerDashboardView,
    FarmerOverviewView,
    FarmerAssignmentsView,
    FarmerEarningsView,
    FarmerPendingActionsView,
)

app_name = 'dashboards'

urlpatterns = [
    # Executive Dashboard Endpoints
    path('executive/', ExecutiveDashboardView.as_view(), name='executive-dashboard'),
    path('executive/overview/', ExecutiveOverviewView.as_view(), name='executive-overview'),
    path('executive/charts/', ExecutiveChartsView.as_view(), name='executive-charts'),
    
    # Officer Dashboard Endpoints
    path('officer/', OfficerDashboardView.as_view(), name='officer-dashboard'),
    path('officer/overview/', OfficerOverviewView.as_view(), name='officer-overview'),
    path('officer/orders/', OfficerOrdersView.as_view(), name='officer-orders'),
    path('officer/orders/<str:order_id>/timeline/', OfficerOrderTimelineView.as_view(), name='officer-order-timeline'),
    
    # Farmer Dashboard Endpoints
    path('farmer/', FarmerDashboardView.as_view(), name='farmer-dashboard'),
    path('farmer/overview/', FarmerOverviewView.as_view(), name='farmer-overview'),
    path('farmer/assignments/', FarmerAssignmentsView.as_view(), name='farmer-assignments'),
    path('farmer/earnings/', FarmerEarningsView.as_view(), name='farmer-earnings'),
    path('farmer/pending-actions/', FarmerPendingActionsView.as_view(), name='farmer-pending-actions'),
]
