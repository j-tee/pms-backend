from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Handles password validation and user creation.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'phone', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'preferred_contact_method',
            'region', 'constituency'
        )
        read_only_fields = ('id',)
    
    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs
    
    def validate_phone(self, value):
        """Validate Ghana phone number format."""
        # Remove spaces and dashes
        phone = value.replace(' ', '').replace('-', '')
        
        # Ghana phone numbers start with 0 and have 10 digits
        # or start with +233 and have 12 digits
        if not (
            (phone.startswith('0') and len(phone) == 10 and phone.isdigit()) or
            (phone.startswith('+233') and len(phone) == 13 and phone[1:].isdigit())
        ):
            raise serializers.ValidationError(
                "Invalid Ghana phone number format. Use: 0XXXXXXXXX or +233XXXXXXXXX"
            )
        
        return value
    
    def create(self, validated_data):
        """Create a new user with encrypted password."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user details.
    Used for retrieving and updating user information.
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'phone', 'first_name', 'last_name',
            'full_name', 'role', 'role_display', 'preferred_contact_method',
            'region', 'constituency', 'is_verified', 'is_active',
            'date_joined', 'last_login_at'
        )
        read_only_fields = (
            'id', 'full_name', 'role_display', 'is_verified',
            'date_joined', 'last_login_at'
        )


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes additional user information.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add custom claims
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'phone': self.user.phone,
            'role': self.user.role,
            'full_name': self.user.get_full_name(),
        }
        
        # Update last login
        self.user.last_login_at = timezone.now()
        self.user.save(update_fields=['last_login_at'])
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change endpoint."""
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """Validate that new passwords match."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password": "New password fields didn't match."}
            )
        return attrs
    
    def validate_old_password(self, value):
        """Validate that old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
