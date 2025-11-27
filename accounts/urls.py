from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    UserRegistrationView,
    CustomTokenObtainPairView,
    UserProfileView,
    ChangePasswordView,
    LogoutView,
    user_list,
)

from .admin_views import (
    AdminStaffInvitationAcceptView,
)

from .mfa_views import (
    mfa_status,
    enable_totp,
    verify_totp_setup,
    enable_sms,
    verify_sms_setup,
    disable_mfa,
    verify_mfa,
    regenerate_backup_codes,
    revoke_trusted_device,
    send_login_code,
)

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Staff invitation (public endpoint)
    path('staff/accept-invitation/', AdminStaffInvitationAcceptView.as_view(), name='staff-accept-invitation'),
    
    # User profile endpoints
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # User management endpoints
    path('users/', user_list, name='user_list'),
    
    # MFA endpoints
    path('mfa/status/', mfa_status, name='mfa_status'),
    path('mfa/totp/enable/', enable_totp, name='enable_totp'),
    path('mfa/totp/verify/', verify_totp_setup, name='verify_totp_setup'),
    path('mfa/sms/enable/', enable_sms, name='enable_sms'),
    path('mfa/sms/verify/', verify_sms_setup, name='verify_sms_setup'),
    path('mfa/disable/', disable_mfa, name='disable_mfa'),
    path('mfa/verify/', verify_mfa, name='verify_mfa'),
    path('mfa/backup-codes/regenerate/', regenerate_backup_codes, name='regenerate_backup_codes'),
    path('mfa/devices/revoke/', revoke_trusted_device, name='revoke_trusted_device'),
    path('mfa/send-code/', send_login_code, name='send_login_code'),
]
