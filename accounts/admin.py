from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.contrib import admin
from core.admin_site import yea_admin_site
from accounts.mfa_models import (
    MFASettings,
    MFAMethod,
    MFABackupCode,
    MFAVerificationCode,
    TrustedDevice
)

User = get_user_model()


class UserAdmin(BaseUserAdmin):
    """Admin interface for the custom User model."""
    
    list_display = (
        'username', 'email', 'phone', 'role', 'region', 'constituency',
        'is_verified', 'is_active', 'is_staff', 'date_joined'
    )
    list_filter = (
        'role', 'is_verified', 'is_active', 'is_staff',
        'region', 'constituency', 'date_joined'
    )
    search_fields = ('username', 'email', 'phone', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'preferred_contact_method')
        }),
        ('Role & Location', {
            'fields': ('role', 'region', 'constituency')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'last_login_at', 'date_joined')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email', 'phone', 'password1', 'password2',
                'first_name', 'last_name', 'role', 'preferred_contact_method',
                'region', 'constituency'
            ),
        }),
    )
    
    
    readonly_fields = ('date_joined', 'last_login', 'last_login_at')


@admin.register(MFASettings, site=yea_admin_site)
class MFASettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_enabled', 'is_enforced', 'backup_codes_remaining', 'last_successful_verification')
    list_filter = ('is_enabled', 'is_enforced', 'remember_device_enabled')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('enabled_at', 'disabled_at', 'backup_codes_generated_at', 'last_successful_verification', 'last_failed_attempt')


@admin.register(MFAMethod, site=yea_admin_site)
class MFAMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_type', 'is_primary', 'is_enabled', 'is_verified', 'last_used_at', 'use_count')
    list_filter = ('method_type', 'is_primary', 'is_enabled', 'is_verified')
    search_fields = ('user__email', 'user__username', 'phone_number', 'email_address')
    readonly_fields = ('verified_at', 'last_used_at', 'use_count', 'created_at', 'updated_at')


@admin.register(MFABackupCode, site=yea_admin_site)
class MFABackupCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_used', 'used_at', 'created_at')
    list_filter = ('is_used',)
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('code_hash', 'used_at', 'used_from_ip', 'created_at')


@admin.register(MFAVerificationCode, site=yea_admin_site)
class MFAVerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('user', 'code_type', 'sent_to', 'is_used', 'verification_attempts', 'expires_at')
    list_filter = ('code_type', 'is_used')
    search_fields = ('user__email', 'user__username', 'sent_to')
    readonly_fields = ('code', 'sent_at', 'used_at', 'created_at')


@admin.register(TrustedDevice, site=yea_admin_site)
class TrustedDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'device_name', 'ip_address', 'is_trusted', 'revoked', 'last_used_at', 'trust_expires_at')
    list_filter = ('is_trusted', 'revoked')
    search_fields = ('user__email', 'user__username', 'device_name', 'ip_address')
    readonly_fields = ('device_fingerprint', 'last_used_at', 'use_count', 'revoked_at', 'created_at', 'updated_at')


# Register with custom admin site
yea_admin_site.register(User, UserAdmin)
