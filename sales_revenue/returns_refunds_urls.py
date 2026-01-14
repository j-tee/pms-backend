"""
URL configuration for Returns and Refunds API endpoints.
"""

from django.urls import path
from .returns_refunds_views import (
    ReturnRequestListCreateView,
    ReturnRequestDetailView,
    approve_return_request,
    mark_items_received,
    issue_refund,
    complete_return,
    return_statistics,
)

app_name = 'returns_refunds'

urlpatterns = [
    # Return request management
    path('', ReturnRequestListCreateView.as_view(), name='return-list-create'),
    path('<uuid:id>/', ReturnRequestDetailView.as_view(), name='return-detail'),
    path('<uuid:return_id>/approve/', approve_return_request, name='return-approve'),
    path('<uuid:return_id>/items-received/', mark_items_received, name='return-items-received'),
    path('<uuid:return_id>/issue-refund/', issue_refund, name='return-issue-refund'),
    path('<uuid:return_id>/complete/', complete_return, name='return-complete'),
    
    # Statistics
    path('statistics/', return_statistics, name='return-statistics'),
]
