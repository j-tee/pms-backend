"""
MFA Views

API endpoints for Multi-Factor Authentication management.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from accounts.services.mfa_service import MFAService
from accounts.mfa_serializers import (
    MFAStatusSerializer,
    EnableTOTPSerializer,
    VerifyTOTPSetupSerializer,
    EnableSMSSerializer,
    VerifySMSSetupSerializer,
    DisableMFASerializer,
    VerifyMFASerializer,
    RegenerateBackupCodesSerializer,
    RevokeTrustedDeviceSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mfa_status(request):
    """
    Get user's MFA status and configuration.
    
    GET /api/auth/mfa/status/
    """
    try:
        status_data = MFAService.get_user_mfa_status(request.user)
        serializer = MFAStatusSerializer(status_data)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_totp(request):
    """
    Enable TOTP (authenticator app) MFA.
    Returns QR code and secret for setup.
    
    POST /api/auth/mfa/totp/enable/
    """
    serializer = EnableTOTPSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        result = MFAService.enable_totp(request.user)
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_totp_setup(request):
    """
    Verify TOTP code to complete MFA setup.
    Returns backup codes.
    
    POST /api/auth/mfa/totp/verify/
    Body: {
        "code": "123456",
        "method_id": "uuid"
    }
    """
    serializer = VerifyTOTPSetupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        result = MFAService.verify_totp_setup(
            request.user,
            serializer.validated_data['code'],
            serializer.validated_data['method_id']
        )
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enable_sms(request):
    """
    Enable SMS MFA.
    Sends verification code to phone.
    
    POST /api/auth/mfa/sms/enable/
    Body: {
        "phone_number": "+233XXXXXXXXX"
    }
    """
    serializer = EnableSMSSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        result = MFAService.enable_sms(
            request.user,
            serializer.validated_data['phone_number']
        )
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_sms_setup(request):
    """
    Verify SMS code to complete MFA setup.
    Returns backup codes.
    
    POST /api/auth/mfa/sms/verify/
    Body: {
        "code": "123456",
        "method_id": "uuid"
    }
    """
    serializer = VerifySMSSetupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        result = MFAService.verify_sms_setup(
            request.user,
            serializer.validated_data['code'],
            serializer.validated_data['method_id']
        )
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def disable_mfa(request):
    """
    Disable MFA for user (requires password).
    
    POST /api/auth/mfa/disable/
    Body: {
        "password": "current_password"
    }
    """
    serializer = DisableMFASerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        result = MFAService.disable_mfa(
            request.user,
            serializer.validated_data['password']
        )
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_mfa(request):
    """
    Verify MFA code for sensitive action.
    
    POST /api/auth/mfa/verify/
    Body: {
        "code": "123456",
        "method_type": "totp",  // optional
        "remember_device": true,  // optional
        "device_name": "My Laptop"  // optional
    }
    """
    serializer = VerifyMFASerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        result = MFAService.verify_mfa(
            request.user,
            serializer.validated_data['code'],
            serializer.validated_data.get('method_type')
        )
        
        # Remember device if requested
        if serializer.validated_data.get('remember_device'):
            device_name = serializer.validated_data.get('device_name', 'Unknown Device')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            ip_address = request.META.get('REMOTE_ADDR', '')
            
            MFAService.add_trusted_device(
                request.user,
                device_name,
                user_agent,
                ip_address
            )
            result['device_trusted'] = True
        
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def regenerate_backup_codes(request):
    """
    Generate new backup codes (invalidates old ones).
    Requires password confirmation.
    
    POST /api/auth/mfa/backup-codes/regenerate/
    Body: {
        "password": "current_password"
    }
    """
    serializer = RegenerateBackupCodesSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    # Verify password
    if not request.user.check_password(serializer.validated_data['password']):
        return Response(
            {'error': 'Invalid password'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        codes = MFAService.generate_backup_codes(request.user)
        return Response(
            {
                'success': True,
                'backup_codes': codes,
                'message': 'New backup codes generated. Save them in a safe place.',
                'warning': 'Old backup codes have been invalidated.'
            },
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_trusted_device(request):
    """
    Revoke a trusted device.
    
    POST /api/auth/mfa/devices/revoke/
    Body: {
        "device_id": "uuid",
        "reason": "Lost device"  // optional
    }
    """
    serializer = RevokeTrustedDeviceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    try:
        result = MFAService.revoke_trusted_device(
            request.user,
            serializer.validated_data['device_id'],
            serializer.validated_data.get('reason', '')
        )
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_login_code(request):
    """
    Send MFA code for login (SMS/Email methods).
    
    POST /api/auth/mfa/send-code/
    """
    try:
        result = MFAService.send_login_code(request.user)
        return Response(result, status=status.HTTP_200_OK)
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
