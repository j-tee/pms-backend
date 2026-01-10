"""
Admin Dashboard URL Configuration
"""

from django.urls import path
from .admin_views import (
    AdminDashboardOverviewView,
    AdminApplicationApproveView,
    AdminApplicationRejectView,
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

# User Management views (suspend, unlock, etc.)
from .user_management_views import (
    AdminUserSuspendView,
    AdminUserUnsuspendView,
    AdminUserResetPasswordView,
    AdminUserUnlockView,
    AdminUserForceLogoutView,
    AdminUserLoginAttemptsView,
    AdminUserLoginHistoryView,
    AdminUserReset2FAView,
    AdminUserSuspensionStatusView,
)

# Batch management views
from .batch_admin_views import (
    AdminBatchListView,
    AdminBatchDetailView,
    AdminBatchCreateView,
    AdminBatchUpdateView,
    AdminBatchDeleteView,
    AdminBatchDetailUpdateDeleteView,
)

# Program action views
from .batch_action_views import (
    AdminBatchToggleActiveView,
    AdminBatchTogglePublishView,
    AdminBatchCloseApplicationsView,
    AdminBatchExtendDeadlineView,
    AdminBatchParticipantsView,
    AdminBatchStatisticsView,
    AdminBatchDuplicateView,
)

# Financial admin views
from .financial_admin_views import (
    PaymentHistoryView,
    RevenueSummaryView,
    ActiveSubscribersView,
    FinanceDashboardView,
)

# AdSense admin views
from .adsense_admin_views import (
    AdSenseStatusView,
    AdSenseConnectView,
    AdSenseCallbackView,
    AdSenseDisconnectView,
    AdSenseEarningsView,
    AdSenseReportsView,
    AdSensePaymentsView,
)

# Permission management views
from .permission_views import (
    PermissionListView,
    UserPermissionsView,
    GrantPermissionView,
    RevokePermissionView,
    ResetPermissionView,
    ManageableUsersView,
)

app_name = 'admin_api'

urlpatterns = [
    # Dashboard Overview
    path('dashboard/overview/', AdminDashboardOverviewView.as_view(), name='admin-overview'),
    
    # ========================================
    # User Management - CRUD
    # ========================================
    path('users/', AdminUserListView.as_view(), name='admin-user-list'),
    path('users/create/', AdminUserCreateView.as_view(), name='admin-user-create'),
    path('users/<uuid:user_id>/', AdminUserDetailView.as_view(), name='admin-user-detail'),
    
    # ========================================
    # User Management - Actions
    # ========================================
    # Suspension
    path('users/<uuid:user_id>/suspend/', AdminUserSuspendView.as_view(), name='admin-user-suspend'),
    path('users/<uuid:user_id>/unsuspend/', AdminUserUnsuspendView.as_view(), name='admin-user-unsuspend'),
    path('users/<uuid:user_id>/suspension-status/', AdminUserSuspensionStatusView.as_view(), name='admin-user-suspension-status'),
    
    # Account Security
    path('users/<uuid:user_id>/unlock/', AdminUserUnlockView.as_view(), name='admin-user-unlock'),
    path('users/<uuid:user_id>/force-logout/', AdminUserForceLogoutView.as_view(), name='admin-user-force-logout'),
    path('users/<uuid:user_id>/reset-password/', AdminUserResetPasswordView.as_view(), name='admin-user-reset-password'),
    path('users/<uuid:user_id>/reset-2fa/', AdminUserReset2FAView.as_view(), name='admin-user-reset-2fa'),
    
    # Login History & Attempts
    path('users/<uuid:user_id>/login-attempts/', AdminUserLoginAttemptsView.as_view(), name='admin-user-login-attempts'),
    path('users/<uuid:user_id>/login-history/', AdminUserLoginHistoryView.as_view(), name='admin-user-login-history'),
    
    # ========================================
    # Permission Management
    # ========================================
    path('permissions/', PermissionListView.as_view(), name='admin-permission-list'),
    path('permissions/manageable-users/', ManageableUsersView.as_view(), name='admin-manageable-users'),
    path('users/<uuid:user_id>/permissions/', UserPermissionsView.as_view(), name='admin-user-permissions'),
    path('users/<uuid:user_id>/permissions/grant/', GrantPermissionView.as_view(), name='admin-grant-permission'),
    path('users/<uuid:user_id>/permissions/revoke/', RevokePermissionView.as_view(), name='admin-revoke-permission'),
    path('users/<uuid:user_id>/permissions/reset/', ResetPermissionView.as_view(), name='admin-reset-permission'),
    
    # ========================================
    # Staff Invitation Management
    # ========================================
    path('staff/<uuid:user_id>/resend-invitation/', AdminStaffInvitationResendView.as_view(), name='admin-staff-resend-invitation'),
    path('staff/<uuid:user_id>/cancel-invitation/', AdminStaffInvitationCancelView.as_view(), name='admin-staff-cancel-invitation'),
    
    # Application Management
    path('applications/', AdminApplicationListView.as_view(), name='admin-application-list'),
    path('applications/<uuid:application_id>/approve/', AdminApplicationApproveView.as_view(), name='admin-application-approve'),
    path('applications/<uuid:application_id>/reject/', AdminApplicationRejectView.as_view(), name='admin-application-reject'),
    
    # ========================================
    # Batch/Program Management (Backward Compatible)
    # Note: 'programs' URLs maintained for backward compatibility
    # 'batches' URLs are the new standard
    # ========================================
    
    # Batch Management - CRUD
    path('batches/', AdminBatchListView.as_view(), name='admin-batch-list'),  # GET & POST
    path('batches/<uuid:batch_id>/', AdminBatchDetailUpdateDeleteView.as_view(), name='admin-batch-detail'),  # GET, PUT, PATCH, DELETE
    
    # Batch Management - Actions
    path('batches/<uuid:batch_id>/toggle-active/', AdminBatchToggleActiveView.as_view(), name='admin-batch-toggle-active'),
    path('batches/<uuid:batch_id>/toggle-publish/', AdminBatchTogglePublishView.as_view(), name='admin-batch-toggle-publish'),
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
    
    # ========================================
    # Financial Reporting
    # ========================================
    
    # Payment History
    path('payments/', PaymentHistoryView.as_view(), name='admin-payments'),
    
    # Revenue Summary
    path('revenue/summary/', RevenueSummaryView.as_view(), name='admin-revenue-summary'),
    
    # Subscribers Management
    path('subscribers/', ActiveSubscribersView.as_view(), name='admin-subscribers'),
    
    # Financial Dashboard
    path('finance/dashboard/', FinanceDashboardView.as_view(), name='admin-finance-dashboard'),
    
    # ========================================
    # AdSense Integration
    # ========================================
    
    # Connection Management (Super Admin only)
    path('adsense/status/', AdSenseStatusView.as_view(), name='admin-adsense-status'),
    path('adsense/connect/', AdSenseConnectView.as_view(), name='admin-adsense-connect'),
    path('adsense/callback/', AdSenseCallbackView.as_view(), name='admin-adsense-callback'),
    path('adsense/disconnect/', AdSenseDisconnectView.as_view(), name='admin-adsense-disconnect'),
    
    # AdSense Data (Finance Viewers)
    path('adsense/earnings/', AdSenseEarningsView.as_view(), name='admin-adsense-earnings'),
    path('adsense/reports/', AdSenseReportsView.as_view(), name='admin-adsense-reports'),
    path('adsense/payments/', AdSensePaymentsView.as_view(), name='admin-adsense-payments'),
]
