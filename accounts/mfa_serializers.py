"""
MFA Serializers

Serializers for Multi-Factor Authentication endpoints.
"""

from rest_framework import serializers
from accounts.mfa_models import MFAMethod, MFASettings, TrustedDevice


class MFAMethodSerializer(serializers.ModelSerializer):
    """Serializer for MFA methods"""
    
    method_display = serializers.CharField(source='get_method_type_display', read_only=True)
    
    class Meta:
        model = MFAMethod
        fields = [
            'id',
            'method_type',
            'method_display',
            'is_primary',
            'is_enabled',
            'is_verified',
            'last_used_at',
            'use_count',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'is_verified',
            'last_used_at',
            'use_count',
            'created_at'
        ]


class TrustedDeviceSerializer(serializers.ModelSerializer):
    """Serializer for trusted devices"""
    
    is_valid = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TrustedDevice
        fields = [
            'id',
            'device_name',
            'ip_address',
            'is_trusted',
            'is_valid',
            'trust_expires_at',
            'last_used_at',
            'use_count',
            'created_at'
        ]
        read_only_fields = [
            'id',
            'ip_address',
            'trust_expires_at',
            'last_used_at',
            'use_count',
            'created_at'
        ]


class MFAStatusSerializer(serializers.Serializer):
    """Serializer for MFA status"""
    
    mfa_enabled = serializers.BooleanField()
    mfa_enforced = serializers.BooleanField()
    methods = MFAMethodSerializer(many=True)
    backup_codes_remaining = serializers.IntegerField()
    trusted_devices = TrustedDeviceSerializer(many=True)
    remember_device_enabled = serializers.BooleanField()


class EnableTOTPSerializer(serializers.Serializer):
    """Serializer for enabling TOTP"""
    
    # No input required
    pass


class VerifyTOTPSetupSerializer(serializers.Serializer):
    """Serializer for verifying TOTP setup"""
    
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        help_text="6-digit code from authenticator app"
    )
    method_id = serializers.UUIDField(help_text="MFA method ID")


class EnableSMSSerializer(serializers.Serializer):
    """Serializer for enabling SMS MFA"""
    
    phone_number = serializers.CharField(
        max_length=20,
        help_text="Phone number to receive SMS codes"
    )


class VerifySMSSetupSerializer(serializers.Serializer):
    """Serializer for verifying SMS setup"""
    
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        help_text="6-digit code sent via SMS"
    )
    method_id = serializers.UUIDField(help_text="MFA method ID")


class DisableMFASerializer(serializers.Serializer):
    """Serializer for disabling MFA"""
    
    password = serializers.CharField(
        write_only=True,
        help_text="Current password for confirmation"
    )


class VerifyMFASerializer(serializers.Serializer):
    """Serializer for verifying MFA code"""
    
    code = serializers.CharField(
        max_length=10,
        help_text="MFA code or backup code (format: XXXX-XXXX)"
    )
    method_type = serializers.ChoiceField(
        choices=['totp', 'sms', 'email'],
        required=False,
        help_text="Specific method to use (optional)"
    )
    remember_device = serializers.BooleanField(
        default=False,
        help_text="Remember this device for 30 days"
    )
    device_name = serializers.CharField(
        required=False,
        help_text="Name for this device (if remember_device=true)"
    )


class RegenerateBackupCodesSerializer(serializers.Serializer):
    """Serializer for regenerating backup codes"""
    
    password = serializers.CharField(
        write_only=True,
        help_text="Current password for confirmation"
    )


class RevokeTrustedDeviceSerializer(serializers.Serializer):
    """Serializer for revoking trusted device"""
    
    device_id = serializers.UUIDField(help_text="Device ID to revoke")
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Reason for revocation (optional)"
    )
