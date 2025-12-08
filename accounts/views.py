from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer
)
from .auth_services import PasswordResetService

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    No authentication required.
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT token obtain view with additional user information.
    """
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint for retrieving and updating user profile.
    Requires authentication.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    API endpoint for changing user password.
    Requires authentication.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        # Set new password
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    API endpoint for user logout.
    Blacklists the refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_list(request):
    """
    API endpoint for listing users.
    Only accessible by admins and officials.
    """
    # Check if user has permission to view user list
    if request.user.role not in ['NATIONAL_ADMIN', 'CONSTITUENCY_OFFICIAL', 'AUDITOR']:
        return Response(
            {'error': 'You do not have permission to access this resource'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Filter users based on role
    if request.user.role == 'CONSTITUENCY_OFFICIAL':
        # Constituency officials can only see users in their constituency
        users = User.objects.filter(constituency=request.user.constituency)
    else:
        # National admins and auditors can see all users
        users = User.objects.all()
    
    # Apply filters from query params
    role = request.GET.get('role')
    if role:
        users = users.filter(role=role)
    
    region = request.GET.get('region')
    if region:
        users = users.filter(region=region)
    
    constituency = request.GET.get('constituency')
    if constituency:
        users = users.filter(constituency=constituency)
    
    is_active = request.GET.get('is_active')
    if is_active is not None:
        users = users.filter(is_active=is_active.lower() == 'true')
    
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


class PasswordResetRequestView(APIView):
    """
    API endpoint for requesting a password reset.
    Sends an email with a reset token.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            PasswordResetService.send_password_reset_email(user)
        except User.DoesNotExist:
            # Silently fail to prevent email enumeration
            pass

        return Response({
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """
    API endpoint for confirming password reset.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        success, error = PasswordResetService.reset_password(token, new_password)

        if success:
            return Response({
                'message': 'Password reset successfully'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)

