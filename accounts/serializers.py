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
            'phone_verified', 'email_verified', 'failed_login_attempts',
            'created_at', 'date_joined', 'last_login_at'
        )
        read_only_fields = (
            'id', 'full_name', 'role_display', 'is_verified',
            'phone_verified', 'email_verified', 'failed_login_attempts',
            'created_at', 'date_joined', 'last_login_at'
        )


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for admin user management.
    Includes all user fields for admin operations.
    
    For FARMER users, location fields (region, district, constituency) are
    computed from their farm profile or application if not set on User model.
    """
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    password = serializers.CharField(write_only=True, required=False)
    suspended_by_name = serializers.SerializerMethodField()
    
    # Computed location fields for farmers
    region = serializers.SerializerMethodField()
    district = serializers.SerializerMethodField()
    constituency = serializers.SerializerMethodField()
    
    # Additional farmer-specific fields
    farm_id = serializers.SerializerMethodField()
    farm_name = serializers.SerializerMethodField()
    location_source = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'phone', 'first_name', 'last_name',
            'full_name', 'role', 'role_display', 'preferred_contact_method',
            'region', 'district', 'constituency', 'is_verified', 'is_active', 'phone_verified',
            'email_verified', 'is_staff', 'date_joined', 'last_login_at',
            'created_at', 'updated_at', 'failed_login_attempts',
            'account_locked_until', 'password',
            # Suspension fields
            'is_suspended', 'suspended_at', 'suspended_until', 'suspended_by',
            'suspended_by_name', 'suspension_reason',
            # Security fields
            'token_version', 'last_failed_login_at',
            # Farmer-specific fields
            'farm_id', 'farm_name', 'location_source'
        )
        read_only_fields = (
            'id', 'full_name', 'role_display', 'date_joined', 'last_login_at',
            'created_at', 'updated_at', 'is_suspended', 'suspended_at',
            'suspended_until', 'suspended_by', 'suspended_by_name',
            'suspension_reason', 'token_version', 'last_failed_login_at',
            'farm_id', 'farm_name', 'location_source'
        )
    
    def _get_farmer_location_data(self, obj):
        """
        Get location data for a farmer from their farm or application.
        Returns dict with region, district, constituency, source, farm_id, farm_name.
        """
        if not hasattr(self, '_farmer_location_cache'):
            self._farmer_location_cache = {}
        
        if obj.id in self._farmer_location_cache:
            return self._farmer_location_cache[obj.id]
        
        location_data = {
            'region': obj.region,
            'district': getattr(obj, 'district', None),
            'constituency': obj.constituency,
            'source': 'user_model' if (obj.region or obj.constituency) else None,
            'farm_id': None,
            'farm_name': None
        }
        
        # Only compute for farmers
        if obj.role != 'FARMER':
            self._farmer_location_cache[obj.id] = location_data
            return location_data
        
        # Try to get from Farm model first
        try:
            from farms.models import Farm
            farm = Farm.objects.filter(user=obj).first()
            if farm:
                location_data['farm_id'] = str(farm.id)
                location_data['farm_name'] = farm.farm_name
                
                # Get location from primary FarmLocation
                primary_location = farm.locations.filter(is_primary_location=True).first()
                if not primary_location:
                    primary_location = farm.locations.first()
                
                if primary_location:
                    location_data['region'] = primary_location.region or location_data['region']
                    location_data['district'] = primary_location.district or location_data['district']
                    location_data['constituency'] = primary_location.constituency or location_data['constituency']
                    location_data['source'] = 'farm_location'
                elif farm.primary_constituency:
                    # Fall back to farm's primary_constituency
                    location_data['constituency'] = farm.primary_constituency
                    location_data['source'] = 'farm_profile'
        except Exception:
            pass
        
        # If still no location data, try FarmApplication
        if not location_data['region'] and not location_data['constituency']:
            try:
                from farms.application_models import FarmApplication
                application = FarmApplication.objects.filter(
                    user_account=obj,
                    status__in=['approved', 'APPROVED', 'Approved']
                ).first()
                
                if not application:
                    # Try pending/submitted applications as fallback
                    application = FarmApplication.objects.filter(user_account=obj).first()
                
                if application:
                    location_data['region'] = application.region or location_data['region']
                    location_data['district'] = application.district or location_data['district']
                    location_data['constituency'] = application.primary_constituency or location_data['constituency']
                    location_data['source'] = 'farm_application'
            except Exception:
                pass
        
        self._farmer_location_cache[obj.id] = location_data
        return location_data
    
    def get_suspended_by_name(self, obj):
        """Get the name of the admin who suspended this user."""
        if obj.suspended_by:
            return obj.suspended_by.get_full_name()
        return None
    
    def get_region(self, obj):
        """Get region - computed for farmers."""
        return self._get_farmer_location_data(obj)['region']
    
    def get_district(self, obj):
        """Get district - computed for farmers."""
        return self._get_farmer_location_data(obj)['district']
    
    def get_constituency(self, obj):
        """Get constituency - computed for farmers."""
        return self._get_farmer_location_data(obj)['constituency']
    
    def get_farm_id(self, obj):
        """Get farm ID if user is a farmer."""
        if obj.role != 'FARMER':
            return None
        return self._get_farmer_location_data(obj)['farm_id']
    
    def get_farm_name(self, obj):
        """Get farm name if user is a farmer."""
        if obj.role != 'FARMER':
            return None
        return self._get_farmer_location_data(obj)['farm_name']
    
    def get_location_source(self, obj):
        """
        Get the source of location data.
        Possible values: 'user_model', 'farm_location', 'farm_profile', 'farm_application', null
        """
        if obj.role != 'FARMER':
            return 'user_model' if (obj.region or obj.constituency) else None
        return self._get_farmer_location_data(obj)['source']
    
    def create(self, validated_data):
        """Create a new user with encrypted password."""
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user
    
    def update(self, instance, validated_data):
        """Update user, handling password separately."""
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that includes additional user information
    and automatic routing based on user role.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Determine if user is a farmer or staff member
        is_farmer = self.user.role == 'FARMER'
        
        # Determine redirect path
        if is_farmer:
            redirect_to = '/farmer/dashboard'
            dashboard_type = 'farmer'
        else:
            redirect_to = '/staff/dashboard'
            dashboard_type = 'staff'
        
        # Add custom claims
        data['user'] = {
            'id': str(self.user.id),
            'username': self.user.username,
            'email': self.user.email,
            'phone': str(self.user.phone) if self.user.phone else None,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'role_display': self.user.get_role_display(),
            'full_name': self.user.get_full_name(),
            'region': self.user.region,
            'constituency': self.user.constituency,
            'is_verified': self.user.is_verified,
            'is_active': self.user.is_active,
        }
        
        # Add routing information
        data['routing'] = {
            'dashboard_type': dashboard_type,
            'redirect_to': redirect_to,
            'is_staff': not is_farmer,
            'is_farmer': is_farmer
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


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset."""
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset."""
    token = serializers.CharField(required=True)
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
