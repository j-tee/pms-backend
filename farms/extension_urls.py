"""
Extension Officer / Field Officer URLs

PRIMARY RESPONSIBILITY: DATA VERIFICATION AND FARMER ASSISTANCE
Field officers ensure farmers are feeding the system with accurate data.

Endpoints for extension officers and constituency vet officers to:
1. DATA VERIFICATION - Review and verify farmer-entered production data
2. DATA ASSISTANCE - Help farmers enter data when they need support
3. FARMER REGISTRATION - Register farmers on behalf (field registration)
4. FARM UPDATES - Update farm information after field visits
5. QUALITY TRACKING - Monitor data quality and flag issues
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
    FarmDataVerificationView,
    FarmerDataAssistanceView,
    DataQualityDashboardView,
)

app_name = 'extension'

urlpatterns = [
    # Dashboard
    path('dashboard/', FieldOfficerDashboardView.as_view(), name='dashboard'),
    
    # Data Quality Dashboard (PRIMARY - shows farms needing attention)
    path('data-quality/', DataQualityDashboardView.as_view(), name='data-quality'),
    
    # Farm Management
    path('farms/', FieldOfficerFarmListView.as_view(), name='farm-list'),
    path('farms/bulk-update/', BulkUpdateFarmsView.as_view(), name='bulk-update'),
    path('farms/<uuid:farm_id>/', FieldOfficerFarmDetailView.as_view(), name='farm-detail'),
    path('farms/<uuid:farm_id>/assign-officer/', AssignExtensionOfficerView.as_view(), name='assign-officer'),
    
    # Data Verification & Assistance (PRIMARY RESPONSIBILITY)
    path('farms/<uuid:farm_id>/data-review/', FarmDataVerificationView.as_view(), name='data-review'),
    path('farms/<uuid:farm_id>/assist-entry/', FarmerDataAssistanceView.as_view(), name='assist-entry'),
    
    # Farmer Registration
    path('register-farmer/', RegisterFarmerView.as_view(), name='register-farmer'),
    
    # Officers
    path('officers/', ListExtensionOfficersView.as_view(), name='officer-list'),
]
