"""
CMS Models
Content management for platform pages (About Us, Privacy Policy, Terms of Service)
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

# Import Help models for easier access
from .help_models import HelpCategory, HelpArticle, HelpArticleFeedback, PopularSearch


class ContentPage(models.Model):
    """
    Content management for static platform pages.
    Only SUPER_ADMIN can create, edit, or delete.
    Public can view published pages.
    """
    
    class PageType(models.TextChoices):
        ABOUT_US = 'about_us', 'About Us'
        PRIVACY_POLICY = 'privacy_policy', 'Privacy Policy'
        TERMS_OF_SERVICE = 'terms_of_service', 'Terms of Service'
        FAQ = 'faq', 'Frequently Asked Questions'
        CONTACT_INFO = 'contact_info', 'Contact Information'
        CUSTOM = 'custom', 'Custom Page'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Page identification
    page_type = models.CharField(
        max_length=50,
        choices=PageType.choices,
        unique=True,
        db_index=True,
        help_text="Type of content page"
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Page title (e.g., 'About YEA Poultry Management System')"
    )
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="URL-friendly identifier (e.g., 'about-us')"
    )
    
    # Content
    content = models.TextField(
        help_text="Full page content (supports Markdown/HTML)"
    )
    
    excerpt = models.TextField(
        blank=True,
        help_text="Short summary or excerpt (optional)"
    )
    
    # Meta information
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text="SEO meta description (160 characters max)"
    )
    
    meta_keywords = models.CharField(
        max_length=255,
        blank=True,
        help_text="SEO keywords (comma-separated)"
    )
    
    # Status and publishing
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Publication status"
    )
    
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Publication date/time"
    )
    
    # Version control
    version = models.IntegerField(
        default=1,
        help_text="Content version number"
    )
    
    # Audit trail
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_pages',
        help_text="User who created this page"
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_pages',
        help_text="User who last updated this page"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft delete
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Deletion timestamp"
    )
    
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_pages',
        help_text="User who deleted this page"
    )
    
    class Meta:
        db_table = 'cms_content_page'
        ordering = ['-updated_at']
        verbose_name = 'Content Page'
        verbose_name_plural = 'Content Pages'
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['page_type', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_page_type_display()} - {self.title}"
    
    def publish(self, user):
        """Publish the page."""
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.updated_by = user
        self.save()
    
    def unpublish(self, user):
        """Unpublish the page (revert to draft)."""
        self.status = self.Status.DRAFT
        self.updated_by = user
        self.save()
    
    def archive(self, user):
        """Archive the page."""
        self.status = self.Status.ARCHIVED
        self.updated_by = user
        self.save()
    
    def soft_delete(self, user):
        """Soft delete the page."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def restore(self):
        """Restore a soft-deleted page."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()


class ContentPageRevision(models.Model):
    """
    Version history for content pages.
    Tracks all changes made to pages.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    page = models.ForeignKey(
        ContentPage,
        on_delete=models.CASCADE,
        related_name='revisions',
        help_text="Content page this revision belongs to"
    )
    
    version = models.IntegerField(
        help_text="Version number"
    )
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    
    # Change tracking
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='page_revisions',
        help_text="User who made this change"
    )
    
    change_summary = models.TextField(
        blank=True,
        help_text="Description of changes made in this revision"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cms_content_page_revision'
        ordering = ['-version']
        verbose_name = 'Content Page Revision'
        verbose_name_plural = 'Content Page Revisions'
        unique_together = [['page', 'version']]
        indexes = [
            models.Index(fields=['page', 'version']),
        ]
    
    def __str__(self):
        return f"{self.page.title} - v{self.version}"


class CompanyProfile(models.Model):
    """
    Company information for Alphalogique Technologies.
    Only SUPER_ADMIN can edit.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Company details
    company_name = models.CharField(
        max_length=255,
        default='Alphalogique Technologies',
        help_text="Company name"
    )
    
    tagline = models.CharField(
        max_length=255,
        blank=True,
        help_text="Company tagline or slogan"
    )
    
    description = models.TextField(
        help_text="Company description"
    )
    
    # Contact information
    email = models.EmailField(help_text="Company email")
    phone = models.CharField(max_length=50, help_text="Company phone")
    website = models.URLField(blank=True, help_text="Company website")
    
    # Address
    address_line1 = models.CharField(max_length=255, help_text="Address line 1")
    address_line2 = models.CharField(max_length=255, blank=True, help_text="Address line 2")
    city = models.CharField(max_length=100, help_text="City")
    region = models.CharField(max_length=100, help_text="Region/State")
    country = models.CharField(max_length=100, default='Ghana', help_text="Country")
    postal_code = models.CharField(max_length=20, blank=True, help_text="Postal code")
    
    # Social media
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    
    # Logo and branding
    logo_url = models.URLField(blank=True, help_text="Company logo URL")
    
    # Audit
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Last updated by"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cms_company_profile'
        verbose_name = 'Company Profile'
        verbose_name_plural = 'Company Profile'
    
    def __str__(self):
        return self.company_name
    
    def save(self, *args, **kwargs):
        """Ensure only one company profile exists."""
        if not self.pk and CompanyProfile.objects.exists():
            raise ValueError("Only one company profile is allowed")
        return super().save(*args, **kwargs)
