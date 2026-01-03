"""
Inventory URL Routes

Farmer endpoints: /api/inventory/
Admin endpoints: /api/admin/inventory/
"""

from django.urls import path
from .inventory_views import (
    FarmInventoryListView,
    FarmInventoryDetailView,
    InventoryAdjustmentView,
    BirdsReadyForMarketView,
    GovernmentInventoryAnalyticsView,
    FarmInventoryInterventionView,
)

app_name = 'inventory'

# Farmer endpoints
urlpatterns = [
    # Inventory list and summary
    path('', FarmInventoryListView.as_view(), name='inventory-list'),
    
    # Inventory detail with movements
    path('<uuid:id>/', FarmInventoryDetailView.as_view(), name='inventory-detail'),
    
    # Manual adjustments (add/remove stock)
    path('<uuid:inventory_id>/adjust/', InventoryAdjustmentView.as_view(), name='inventory-adjust'),
    
    # Birds ready for market
    path('birds-ready/', BirdsReadyForMarketView.as_view(), name='birds-ready'),
]

# Admin/Government endpoints (to be included under /api/admin/)
admin_urlpatterns = [
    # Government analytics dashboard
    path('analytics/', GovernmentInventoryAnalyticsView.as_view(), name='inventory-analytics'),
    
    # Specific farm intervention view
    path('farms/<uuid:farm_id>/', FarmInventoryInterventionView.as_view(), name='farm-intervention'),
]
