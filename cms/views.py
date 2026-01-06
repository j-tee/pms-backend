"""
CMS Views
Content management views for platform pages.
"""
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404

from .models import ContentPage, ContentPageRevision, CompanyProfile
from .serializers import (
    ContentPageListSerializer,
    ContentPageDetailSerializer,
    ContentPagePublicSerializer,
    ContentPageCreateUpdateSerializer,
    ContentPageRevisionSerializer,
    CompanyProfileSerializer
)
from .permissions import IsSuperAdminOnly, CanManageContent, CanViewCompanyProfile


class ContentPageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for content pages (About Us, Privacy Policy, etc.)
    
    Permissions:
    - GET (public): Only published pages
    - POST/PUT/PATCH/DELETE: SUPER_ADMIN only
    """
    queryset = ContentPage.objects.filter(is_deleted=False)
    permission_classes = [CanManageContent]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return ContentPageListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ContentPageCreateUpdateSerializer
        elif self.action == 'retrieve':
            # Admin gets full details, public gets limited
            if self.request.user and self.request.user.role == 'SUPER_ADMIN':
                return ContentPageDetailSerializer
            return ContentPagePublicSerializer
        return ContentPageDetailSerializer
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        queryset = super().get_queryset()
        
        # SUPER_ADMIN sees all pages (including drafts)
        if self.request.user and self.request.user.role == 'SUPER_ADMIN':
            return queryset
        
        # COMPANY_ADMIN sees all published pages
        if self.request.user and self.request.user.role == 'COMPANY_ADMIN':
            return queryset.filter(status='published')
        
        # Public sees only published pages
        return queryset.filter(status='published')
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdminOnly])
    def publish(self, request, pk=None):
        """Publish a content page."""
        page = self.get_object()
        page.publish(request.user)
        serializer = ContentPageDetailSerializer(page)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdminOnly])
    def unpublish(self, request, pk=None):
        """Unpublish a content page (revert to draft)."""
        page = self.get_object()
        page.unpublish(request.user)
        serializer = ContentPageDetailSerializer(page)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdminOnly])
    def archive(self, request, pk=None):
        """Archive a content page."""
        page = self.get_object()
        page.archive(request.user)
        serializer = ContentPageDetailSerializer(page)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[IsSuperAdminOnly])
    def revisions(self, request, pk=None):
        """Get revision history for a page."""
        page = self.get_object()
        revisions = page.revisions.all()
        serializer = ContentPageRevisionSerializer(revisions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdminOnly])
    def restore_revision(self, request, pk=None):
        """Restore a specific revision."""
        page = self.get_object()
        revision_id = request.data.get('revision_id')
        
        if not revision_id:
            return Response(
                {'error': 'revision_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        revision = get_object_or_404(ContentPageRevision, id=revision_id, page=page)
        
        # Restore content from revision
        page.title = revision.title
        page.content = revision.content
        page.excerpt = revision.excerpt
        page.version += 1
        page.updated_by = request.user
        page.save()
        
        # Create new revision for the restore
        ContentPageRevision.objects.create(
            page=page,
            version=page.version,
            title=page.title,
            content=page.content,
            excerpt=page.excerpt,
            changed_by=request.user,
            change_summary=f"Restored from version {revision.version}"
        )
        
        serializer = ContentPageDetailSerializer(page)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete content page."""
        page = self.get_object()
        page.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicContentPageView(generics.RetrieveAPIView):
    """
    Public view for fetching content pages by slug.
    No authentication required.
    """
    queryset = ContentPage.objects.filter(status='published', is_deleted=False)
    serializer_class = ContentPagePublicSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class AboutUsView(generics.RetrieveAPIView):
    """
    Dedicated endpoint for About Us page.
    Public access, no auth required.
    """
    serializer_class = ContentPagePublicSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        """Get the About Us page."""
        return get_object_or_404(
            ContentPage,
            page_type='about_us',
            status='published',
            is_deleted=False
        )


class PrivacyPolicyView(generics.RetrieveAPIView):
    """
    Dedicated endpoint for Privacy Policy page.
    Public access, no auth required.
    """
    serializer_class = ContentPagePublicSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        """Get the Privacy Policy page."""
        return get_object_or_404(
            ContentPage,
            page_type='privacy_policy',
            status='published',
            is_deleted=False
        )


class TermsOfServiceView(generics.RetrieveAPIView):
    """
    Dedicated endpoint for Terms of Service page.
    Public access, no auth required.
    """
    serializer_class = ContentPagePublicSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        """Get the Terms of Service page."""
        return get_object_or_404(
            ContentPage,
            page_type='terms_of_service',
            status='published',
            is_deleted=False
        )


class CompanyProfileView(generics.RetrieveUpdateAPIView):
    """
    Company profile management.
    
    Permissions:
    - GET: SUPER_ADMIN or COMPANY_ADMIN
    - PUT/PATCH: SUPER_ADMIN only
    """
    serializer_class = CompanyProfileSerializer
    permission_classes = [CanViewCompanyProfile]
    
    def get_object(self):
        """Get the company profile (singleton)."""
        profile, _ = CompanyProfile.objects.get_or_create(
            defaults={
                'company_name': 'Alphalogique Technologies',
                'email': 'info@alphalogique.com',
                'phone': '+233XXXXXXXXX',
                'description': 'Technology solutions for agricultural development.',
                'address_line1': 'Accra, Ghana',
                'city': 'Accra',
                'region': 'Greater Accra',
                'country': 'Ghana'
            }
        )
        return profile
    
    def perform_update(self, serializer):
        """Update company profile."""
        serializer.save(updated_by=self.request.user)
