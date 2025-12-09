"""Mortality management API routes."""

from django.urls import path

from .views import MortalityRecordDetailView, MortalityRecordView

app_name = 'mortality'

urlpatterns = [
    path('pending-inspection/', MortalityRecordView.as_view(), {'pending_only': True}, name='pending-inspection'),
    path('<uuid:record_id>/', MortalityRecordDetailView.as_view(), name='mortality-detail'),
    path('', MortalityRecordView.as_view(), name='mortality'),
]
