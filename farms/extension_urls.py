"""
Extension Officer / Field Officer URLs

Endpoints for extension officers and constituency vet officers to:
- Register farmers on behalf (field registration)
- Update farm information
- View and manage assigned farms
- Conduct extension duties
"""

from django.urls import path
from .extension_views import (
    FieldOfficerDashboardView,
    FieldOfficerFarmListView,
    FieldOfficerFarmDetailView,
    RegisterFarmerView,
    AssignExtensionOfficerView,
    ListExtensionOfficersView,
    BulkUpdateFarmsView,
)

app_name = 'extension'

urlpatterns = [
    # Dashboard
    path('dashboard/', FieldOfficerDashboardView.as_view(), name='dashboard'),
    
    # Farm Management
    path('farms/', FieldOfficerFarmListView.as_view(), name='farm-list'),
    path('farms/bulk-update/', BulkUpdateFarmsView.as_view(), name='bulk-update'),
    path('farms/<uuid:farm_id>/', FieldOfficerFarmDetailView.as_view(), name='farm-detail'),
    path('farms/<uuid:farm_id>/assign-officer/', AssignExtensionOfficerView.as_view(), name='assign-officer'),
    
    # Farmer Registration
    path('register-farmer/', RegisterFarmerView.as_view(), name='register-farmer'),
    
    # Officers
    path('officers/', ListExtensionOfficersView.as_view(), name='officer-list'),
]
