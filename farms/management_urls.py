"""
Authenticated Farm Management URLs

Provides endpoints for farmers to manage their farm profiles.
All endpoints require authentication and farmer role.
"""
from django.urls import path
from .views import (
    FarmProfileView,
    FarmLocationsView,
    FarmInfrastructureView,
    FarmEquipmentView,
    FarmDocumentsView,
)

app_name = 'farms_management'

urlpatterns = [
    # Farm Profile
    path('profile/', FarmProfileView.as_view(), name='farm-profile'),
    
    # Farm Locations
    path('locations/', FarmLocationsView.as_view(), name='farm-locations'),
    
    # Infrastructure (Poultry Houses)
    path('infrastructure/', FarmInfrastructureView.as_view(), name='farm-infrastructure'),
    
    # Equipment
    path('equipment/', FarmEquipmentView.as_view(), name='farm-equipment'),
    
    # Documents
    path('documents/', FarmDocumentsView.as_view(), name='farm-documents'),
]
