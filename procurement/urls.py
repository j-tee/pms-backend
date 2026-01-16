"""
Procurement URL Configuration

Provides clear separation between:
1. Farmer Procurement Views - /api/procurement/farmer/
   - Farmers viewing their assignments, earnings, deliveries
   
2. Admin Procurement Views - /api/admin/procurement/
   - YEA Staff, Procurement Officers, National Admin managing orders
"""

from django.urls import path

# Import views from dashboards (we'll create dedicated views later)
from dashboards.views import (
    # Farmer Procurement Views
    FarmerDashboardView,
    FarmerOverviewView,
    FarmerAssignmentsView,
    FarmerEarningsView,
    FarmerPendingActionsView,
)

app_name = 'procurement'

# =============================================================================
# FARMER PROCUREMENT URLS
# These endpoints are for farmers to view their procurement assignments
# =============================================================================
farmer_urlpatterns = [
    # Full farmer procurement dashboard
    path('', FarmerDashboardView.as_view(), name='farmer-dashboard'),
    
    # Overview stats
    path('overview/', FarmerOverviewView.as_view(), name='farmer-overview'),
    
    # Assignments from government orders
    path('assignments/', FarmerAssignmentsView.as_view(), name='farmer-assignments'),
    
    # Earnings from procurement
    path('earnings/', FarmerEarningsView.as_view(), name='farmer-earnings'),
    
    # Pending actions (accept/reject, mark ready, etc.)
    path('pending-actions/', FarmerPendingActionsView.as_view(), name='farmer-pending-actions'),
]
