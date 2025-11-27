"""
Admin Dashboard URL Configuration
"""

from django.urls import path
from .admin_views import (
    AdminDashboardOverviewView,
    AdminUserListView,
    AdminUserDetailView,
    AdminUserCreateView,
    AdminApplicationListView,
    AdminAnalyticsView,
    AdminSystemConfigView,
    AdminStaffInvitationAcceptView,
    AdminStaffInvitationResendView,
    AdminStaffInvitationCancelView,
)

# Batch management views
from .batch_admin_views import (
    AdminBatchListView,
    AdminBatchDetailView,
    AdminBatchCreateView,
    AdminBatchUpdateView,
    AdminBatchDeleteView,
)

# Program action views
from .batch_action_views import (
    AdminBatchToggleActiveView,
    AdminBatchCloseApplicationsView,
    AdminBatchExtendDeadlineView,
    AdminBatchParticipantsView,
    AdminBatchStatisticsView,
    AdminBatchDuplicateView,
)

app_name = 'admin_api'

urlpatterns = [
    # Dashboard Overview
    path('dashboard/overview/', AdminDashboardOverviewView.as_view(), name='admin-overview'),
    
    # User Management
    path('users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('users/create/', AdminUserCreateView.as_view(), name='admin-user-create'),
    path('users/<uuid:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    
    # Staff Invitation Management
    path('staff/<uuid:user_id>/resend-invitation/', AdminStaffInvitationResendView.as_view(), name='admin-staff-resend-invitation'),
    path('staff/<uuid:user_id>/cancel-invitation/', AdminStaffInvitationCancelView.as_view(), name='admin-staff-cancel-invitation'),
    
    # Application Management
    path('applications/', AdminApplicationListView.as_view(), name='admin-application-list'),
    
    # ========================================
    # Batch/Program Management (Backward Compatible)
    # Note: 'programs' URLs maintained for backward compatibility
    # 'batches' URLs are the new standard
    # ========================================
    
    # Batch Management - CRUD
    path('batches/', AdminBatchListView.as_view(), name='admin-batch-list'),  # GET & POST
    path('batches/<uuid:batch_id>/', AdminBatchDetailView.as_view(), name='admin-batch-detail'),  # GET
    path('batches/<uuid:batch_id>/', AdminBatchUpdateView.as_view(), name='admin-batch-update'),  # PUT/PATCH
    path('batches/<uuid:batch_id>/', AdminBatchDeleteView.as_view(), name='admin-batch-delete'),  # DELETE
    
    # Batch Management - Actions
    path('batches/<uuid:batch_id>/toggle-active/', AdminBatchToggleActiveView.as_view(), name='admin-batch-toggle-active'),
    path('batches/<uuid:batch_id>/close-applications/', AdminBatchCloseApplicationsView.as_view(), name='admin-batch-close-applications'),
    path('batches/<uuid:batch_id>/extend-deadline/', AdminBatchExtendDeadlineView.as_view(), name='admin-batch-extend-deadline'),
    path('batches/<uuid:batch_id>/duplicate/', AdminBatchDuplicateView.as_view(), name='admin-batch-duplicate'),
    
    # Batch Management - Data
    path('batches/<uuid:batch_id>/participants/', AdminBatchParticipantsView.as_view(), name='admin-batch-participants'),
    path('batches/<uuid:batch_id>/statistics/', AdminBatchStatisticsView.as_view(), name='admin-batch-statistics'),
    
    # ========================================
    # DEPRECATED: Program URLs (for backward compatibility only)
    # Use /batches/ endpoints instead
    # ========================================
                                            
    # Analytics
    path('analytics/', AdminAnalyticsView.as_view(), name='admin-analytics'),
    
    # System Configuration
    path('config/', AdminSystemConfigView.as_view(), name='admin-config'),
]
