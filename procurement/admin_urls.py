"""
Admin Procurement URL Configuration

These endpoints are for YEA Staff, Procurement Officers, and National Admin
to manage government procurement orders.

URL Prefix: /api/admin/procurement/
"""

from django.urls import path

# Import admin views from dashboards
from dashboards.views import (
    # Admin/Officer Procurement Views
    OfficerDashboardView,
    OfficerOverviewView,
    OfficerOrdersView,
    OfficerOrderTimelineView,
    OfficerInvoicesView,
    OfficerDeliveriesView,
    # Distress-based farm selection
    DistressSummaryView,
    DistressedFarmersView,
    FarmDistressDetailView,
    OrderFarmRecommendationsView,
    OrderRecommendationsView,
)

app_name = 'admin_procurement'

urlpatterns = [
    # Full admin procurement dashboard
    path('', OfficerDashboardView.as_view(), name='dashboard'),
    
    # Overview stats
    path('overview/', OfficerOverviewView.as_view(), name='overview'),
    
    # Orders management
    path('orders/', OfficerOrdersView.as_view(), name='orders'),
    
    # Order timeline
    path('orders/<str:order_id>/timeline/', OfficerOrderTimelineView.as_view(), name='order-timeline'),
    
    # Farm recommendations for an order (prioritized by distress)
    path('orders/<str:order_id>/recommend-farms/', OrderFarmRecommendationsView.as_view(), name='order-recommend-farms'),
    
    # Invoices management
    path('invoices/', OfficerInvoicesView.as_view(), name='invoices'),
    
    # Deliveries management
    path('deliveries/', OfficerDeliveriesView.as_view(), name='deliveries'),
    
    # === DISTRESSED FARMERS (Social Welfare Feature) ===
    
    # Distress summary dashboard (overview stats, by region, by type, trends)
    path('distress-summary/', DistressSummaryView.as_view(), name='distress-summary'),
    
    # List all distressed farmers prioritized for procurement
    path('distressed-farmers/', DistressedFarmersView.as_view(), name='distressed-farmers'),
    
    # Alternative URL path matching frontend spec
    path('farmers/distressed/', DistressedFarmersView.as_view(), name='farmers-distressed'),
    
    # AI-powered order recommendations (global, not per-order)
    path('order-recommendations/', OrderRecommendationsView.as_view(), name='order-recommendations'),
    
    # Get distress details for a specific farm
    path('farms/<str:farm_id>/distress/', FarmDistressDetailView.as_view(), name='farm-distress'),
]