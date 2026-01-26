"""
Help Files System Models

Comprehensive help/knowledge base system for end users.
Provides searchable help articles organized by categories.
"""
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()


class HelpCategory(models.Model):
    """
    Categories for organizing help articles.
    Examples: Getting Started, Account Management, Marketplace, Farm Management, etc.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Category name (e.g., 'Getting Started', 'Account Management')"
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="URL-friendly identifier"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Brief description of what this category covers"
    )
    
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon identifier (e.g., 'question-circle', 'user', 'shopping-cart')"
    )
    
    # Ordering
    display_order = models.IntegerField(
        default=0,
        help_text="Order in which categories appear (lower = first)"
    )
    
    # Target audience
    class Audience(models.TextChoices):
        ALL = 'all', 'All Users'
        FARMERS = 'farmers', 'Farmers Only'
        BUYERS = 'buyers', 'Buyers Only'
        STAFF = 'staff', 'Staff/Officials Only'
    
    target_audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.ALL,
        help_text="Who should see this category"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this category is visible to users"
    )
    
    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_help_categories'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cms_help_category'
        ordering = ['display_order', 'name']
        verbose_name = 'Help Category'
        verbose_name_plural = 'Help Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    @property
    def article_count(self):
        """Number of published articles in this category."""
        return self.articles.filter(status='published', is_deleted=False).count()


class HelpArticle(models.Model):
    """
    Individual help articles/documentation.
    Searchable, categorized, and versioned.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Categorization
    category = models.ForeignKey(
        HelpCategory,
        on_delete=models.SET_NULL,
        null=True,
        related_name='articles',
        help_text="Category this article belongs to"
    )
    
    # Content identification
    title = models.CharField(
        max_length=255,
        help_text="Article title (e.g., 'How to Register Your Farm')"
    )
    
    slug = models.SlugField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="URL-friendly identifier"
    )
    
    # Summary for listings/search results
    summary = models.TextField(
        max_length=500,
        help_text="Brief summary shown in search results and listings"
    )
    
    # Full content
    content = models.TextField(
        help_text="Full article content (supports HTML/Markdown)"
    )
    
    # Search optimization
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated keywords for search optimization"
    )
    
    # Target audience (inherits from category but can be overridden)
    target_audience = models.CharField(
        max_length=20,
        choices=HelpCategory.Audience.choices,
        default=HelpCategory.Audience.ALL,
        help_text="Who should see this article (overrides category if set)"
    )
    
    # Related articles
    related_articles = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        help_text="Related articles to show at the bottom"
    )
    
    # Status and publishing
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the article was published"
    )
    
    # Ordering within category
    display_order = models.IntegerField(
        default=0,
        help_text="Order within category (lower = first)"
    )
    
    # Engagement metrics
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this article has been viewed"
    )
    
    helpful_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of users who found this helpful"
    )
    
    not_helpful_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of users who did not find this helpful"
    )
    
    # Version control
    version = models.IntegerField(default=1)
    
    # Audit
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_help_articles'
    )
    
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_help_articles'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Soft delete
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_help_articles'
    )
    
    class Meta:
        db_table = 'cms_help_article'
        ordering = ['category__display_order', 'display_order', 'title']
        verbose_name = 'Help Article'
        verbose_name_plural = 'Help Articles'
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['target_audience', 'status']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def publish(self, user):
        """Publish the article."""
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.updated_by = user
        self.save()
    
    def unpublish(self, user):
        """Unpublish (revert to draft)."""
        self.status = self.Status.DRAFT
        self.updated_by = user
        self.save()
    
    def archive(self, user):
        """Archive the article."""
        self.status = self.Status.ARCHIVED
        self.updated_by = user
        self.save()
    
    def soft_delete(self, user):
        """Soft delete the article."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()
    
    def increment_view(self):
        """Increment view count."""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def mark_helpful(self, helpful: bool):
        """Record feedback."""
        if helpful:
            self.helpful_count += 1
        else:
            self.not_helpful_count += 1
        self.save(update_fields=['helpful_count', 'not_helpful_count'])
    
    @property
    def helpfulness_score(self):
        """Calculate helpfulness percentage."""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return None
        return round((self.helpful_count / total) * 100, 1)


class HelpArticleFeedback(models.Model):
    """
    User feedback on help articles.
    Tracks whether users found articles helpful and allows comments.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    article = models.ForeignKey(
        HelpArticle,
        on_delete=models.CASCADE,
        related_name='feedback'
    )
    
    # Optional user (can be anonymous)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='help_article_feedback'
    )
    
    # Session ID for anonymous users
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Session ID for anonymous feedback tracking"
    )
    
    is_helpful = models.BooleanField(
        help_text="Did the user find this article helpful?"
    )
    
    comment = models.TextField(
        blank=True,
        help_text="Optional feedback comment"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cms_help_article_feedback'
        ordering = ['-created_at']
        verbose_name = 'Article Feedback'
        verbose_name_plural = 'Article Feedback'
        # Prevent duplicate feedback from same user/session per article
        unique_together = [
            ['article', 'user'],
        ]
    
    def __str__(self):
        status = "helpful" if self.is_helpful else "not helpful"
        return f"Feedback on '{self.article.title}' - {status}"


class PopularSearch(models.Model):
    """
    Track popular search terms to improve help content.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    search_term = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )
    
    search_count = models.PositiveIntegerField(default=1)
    
    # Track if search had results
    has_results = models.BooleanField(
        default=True,
        help_text="Did this search return results?"
    )
    
    last_searched = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cms_popular_search'
        ordering = ['-search_count']
        verbose_name = 'Popular Search'
        verbose_name_plural = 'Popular Searches'
    
    def __str__(self):
        return f"{self.search_term} ({self.search_count} searches)"
    
    @classmethod
    def record_search(cls, term: str, has_results: bool = True):
        """Record a search term."""
        term = term.strip().lower()[:255]
        if not term:
            return
        
        obj, created = cls.objects.get_or_create(
            search_term=term,
            defaults={'has_results': has_results}
        )
        
        if not created:
            obj.search_count += 1
            obj.has_results = has_results
            obj.save(update_fields=['search_count', 'has_results', 'last_searched'])
