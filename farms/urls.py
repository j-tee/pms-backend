"""
Public Farm Application URLs
"""
from django.urls import path
from .public_views import (
    SubmitFarmApplicationView,
    TrackApplicationView,
    ApplicationStatisticsView,
    PublicBatchListView,
)

app_name = 'farms'

urlpatterns = [
    # Public application endpoints (no authentication required)
    path('applications/submit/', SubmitFarmApplicationView.as_view(), name='submit-application'),
    path('applications/track/<str:ghana_card_number>/', TrackApplicationView.as_view(), name='track-application'),
    path('applications/statistics/', ApplicationStatisticsView.as_view(), name='application-statistics'),
    
    # Public batch/program endpoints
    path('public/batches/', PublicBatchListView.as_view(), name='public-batches'),
]
