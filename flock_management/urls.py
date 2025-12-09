"""
Flock Management URLs

Provides endpoints for managing bird flocks/batches.
"""
from django.urls import include, path
from .views import DailyProductionView, FlockView, FlockStatisticsView, HealthRecordView

app_name = 'flock_management'

urlpatterns = [
    # Statistics (must come before detail routes)
    path('statistics/', FlockStatisticsView.as_view(), name='flock-statistics'),

    # Daily production records
    path('production/', DailyProductionView.as_view(), name='daily-production'),

    # Nested mortality routes under /api/flocks/mortality/
    path('mortality/', include('flock_management.mortality_urls')),

    # Health records
    path('health/', HealthRecordView.as_view(), name='health-records'),
    
    # Active flocks filter
    path('active/', FlockView.as_view(), {'active_only': True}, name='active-flocks'),
    
    # CRUD operations
    path('', FlockView.as_view(), name='flocks'),
    path('<uuid:flock_id>/', FlockView.as_view(), name='flock-detail'),
]
