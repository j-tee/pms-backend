"""
CMS Serializers
"""
from rest_framework import serializers
from .models import ContentPage, ContentPageRevision, CompanyProfile
from django.contrib.auth import get_user_model

User = get_user_model()


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user information for audit fields."""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


class ContentPageListSerializer(serializers.ModelSerializer):
    """Serializer for listing content pages."""
    page_type_display = serializers.CharField(source='get_page_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by = UserMinimalSerializer(read_only=True)
    updated_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = ContentPage
        fields = [
            'id', 'page_type', 'page_type_display', 'title', 'slug',
            'excerpt', 'status', 'status_display', 'published_at',
            'version', 'created_by', 'updated_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']


class ContentPageDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed content page view."""
    page_type_display = serializers.CharField(source='get_page_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by = UserMinimalSerializer(read_only=True)
    updated_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = ContentPage
        fields = [
            'id', 'page_type', 'page_type_display', 'title', 'slug',
            'content', 'excerpt', 'meta_description', 'meta_keywords',
            'status', 'status_display', 'published_at', 'version',
            'created_by', 'updated_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version', 'created_by', 'updated_by']


class ContentPagePublicSerializer(serializers.ModelSerializer):
    """Public serializer - only show published content."""
    page_type_display = serializers.CharField(source='get_page_type_display', read_only=True)
    
    class Meta:
        model = ContentPage
        fields = [
            'id', 'page_type', 'page_type_display', 'title', 'slug',
            'content', 'excerpt', 'meta_description', 'published_at'
        ]
        read_only_fields = fields


class ContentPageCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating content pages (SUPER_ADMIN only)."""
    change_summary = serializers.CharField(
        write_only=True,
        required=False,
        help_text="Description of changes (for version history)"
    )
    
    class Meta:
        model = ContentPage
        fields = [
            'page_type', 'title', 'slug', 'content', 'excerpt',
            'meta_description', 'meta_keywords', 'status', 'change_summary'
        ]
    
    def validate_slug(self, value):
        """Ensure slug is unique."""
        instance = self.instance
        if instance and instance.slug == value:
            return value
        
        if ContentPage.objects.filter(slug=value).exists():
            raise serializers.ValidationError("A page with this slug already exists.")
        return value
    
    def validate_page_type(self, value):
        """Ensure page_type is unique."""
        instance = self.instance
        if instance and instance.page_type == value:
            return value
        
        if ContentPage.objects.filter(page_type=value).exists():
            raise serializers.ValidationError(f"A {value} page already exists.")
        return value
    
    def create(self, validated_data):
        """Create new content page."""
        change_summary = validated_data.pop('change_summary', '')
        user = self.context['request'].user
        
        # Create page
        page = ContentPage.objects.create(
            **validated_data,
            created_by=user,
            updated_by=user
        )
        
        # Create initial revision
        ContentPageRevision.objects.create(
            page=page,
            version=1,
            title=page.title,
            content=page.content,
            excerpt=page.excerpt,
            changed_by=user,
            change_summary=change_summary or "Initial version"
        )
        
        return page
    
    def update(self, instance, validated_data):
        """Update content page and create revision."""
        change_summary = validated_data.pop('change_summary', '')
        user = self.context['request'].user
        
        # Update page
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.updated_by = user
        instance.version += 1
        instance.save()
        
        # Create revision
        ContentPageRevision.objects.create(
            page=instance,
            version=instance.version,
            title=instance.title,
            content=instance.content,
            excerpt=instance.excerpt,
            changed_by=user,
            change_summary=change_summary or f"Update v{instance.version}"
        )
        
        return instance


class ContentPageRevisionSerializer(serializers.ModelSerializer):
    """Serializer for content page revisions."""
    changed_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = ContentPageRevision
        fields = [
            'id', 'version', 'title', 'content', 'excerpt',
            'changed_by', 'change_summary', 'created_at'
        ]
        read_only_fields = fields


class CompanyProfileSerializer(serializers.ModelSerializer):
    """Serializer for company profile."""
    updated_by = UserMinimalSerializer(read_only=True)
    
    class Meta:
        model = CompanyProfile
        fields = [
            'id', 'company_name', 'tagline', 'description',
            'email', 'phone', 'website',
            'address_line1', 'address_line2', 'city', 'region', 'country', 'postal_code',
            'facebook_url', 'twitter_url', 'linkedin_url', 'instagram_url',
            'logo_url', 'updated_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'updated_by', 'created_at', 'updated_at']
