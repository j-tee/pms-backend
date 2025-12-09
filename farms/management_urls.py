"""
Authenticated Farm Management URLs

Provides endpoints for farmers to manage their farm profiles.
All endpoints require authentication and farmer role.
"""
from django.urls import path
from .views import (
    FarmProfileView,
    FarmLocationsView,
    UnifiedInfrastructureView,
    FarmEquipmentView,
    FarmDocumentsView,
)

app_name = 'farms_management'

urlpatterns = [
    # Farm Profile
    path('profile/', FarmProfileView.as_view(), name='farm-profile'),
    
    # Farm Locations
    path('locations/', FarmLocationsView.as_view(), name='farm-locations'),
    
    # Unified Infrastructure (Both poultry houses and farm systems)
    # Frontend filters by 'category' field: 'poultry_house' or 'farm_system'
    path('infrastructure/', UnifiedInfrastructureView.as_view(), name='infrastructure'),
    path('infrastructure/<uuid:infrastructure_id>/', UnifiedInfrastructureView.as_view(), name='infrastructure-detail'),
    
    # Equipment (Movable operational items: feeders, drinkers, etc.)
    path('equipment/', FarmEquipmentView.as_view(), name='farm-equipment'),
    path('equipment/<uuid:equipment_id>/', FarmEquipmentView.as_view(), name='farm-equipment-detail'),
    
    # Documents (EOI-aligned structure: file + document_type only)
    path('documents/', FarmDocumentsView.as_view(), name='farm-documents'),
    path('documents/<uuid:document_id>/', FarmDocumentsView.as_view(), name='farm-document-detail'),
]
