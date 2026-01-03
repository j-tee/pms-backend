"""
URL configuration for Processing operations.

Endpoints:
- /api/processing/batches/ - Processing batch CRUD
- /api/processing/outputs/ - Processing output CRUD
- /api/processing/analytics/ - Analytics (via viewset action)
- /api/processing/stale-stock/ - Stale stock report for government
- /api/processing/flock/{flock_id}/history/ - Flock processing history
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .processing_views import (
    ProcessingBatchViewSet,
    ProcessingOutputViewSet,
    StaleStockReportView,
    FlockProcessingHistoryView
)

# Create router for viewsets
router = DefaultRouter()
router.register(r'batches', ProcessingBatchViewSet, basename='processing-batch')
router.register(r'outputs', ProcessingOutputViewSet, basename='processing-output')

app_name = 'processing'

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # Government reports
    path('stale-stock/', StaleStockReportView.as_view(), name='stale-stock-report'),
    
    # Flock processing history
    path('flock/<uuid:flock_id>/history/', FlockProcessingHistoryView.as_view(), name='flock-processing-history'),
]
