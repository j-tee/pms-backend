"""
Help Files Serializers
"""
from rest_framework import serializers
from .help_models import HelpCategory, HelpArticle, HelpArticleFeedback, PopularSearch


class HelpCategoryListSerializer(serializers.ModelSerializer):
    """Serializer for listing help categories."""
    article_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = HelpCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'display_order', 'target_audience', 'article_count'
        ]


class HelpCategoryDetailSerializer(serializers.ModelSerializer):
    """Serializer for category detail with articles."""
    article_count = serializers.IntegerField(read_only=True)
    articles = serializers.SerializerMethodField()
    
    class Meta:
        model = HelpCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'display_order', 'target_audience', 'article_count', 'articles'
        ]
    
    def get_articles(self, obj):
        """Get published articles in this category."""
        articles = obj.articles.filter(
            status='published',
            is_deleted=False
        ).order_by('display_order', 'title')
        return HelpArticleListSerializer(articles, many=True).data


class HelpArticleListSerializer(serializers.ModelSerializer):
    """Serializer for listing help articles."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    helpfulness_score = serializers.FloatField(read_only=True)
    
    class Meta:
        model = HelpArticle
        fields = [
            'id', 'title', 'slug', 'summary',
            'category', 'category_name', 'category_slug',
            'target_audience', 'display_order',
            'view_count', 'helpfulness_score',
            'published_at'
        ]


class HelpArticleDetailSerializer(serializers.ModelSerializer):
    """Serializer for full article detail."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    helpfulness_score = serializers.FloatField(read_only=True)
    related_articles = HelpArticleListSerializer(many=True, read_only=True)
    
    class Meta:
        model = HelpArticle
        fields = [
            'id', 'title', 'slug', 'summary', 'content', 'keywords',
            'category', 'category_name', 'category_slug',
            'target_audience', 'display_order',
            'view_count', 'helpful_count', 'not_helpful_count', 'helpfulness_score',
            'related_articles',
            'published_at', 'updated_at'
        ]


class HelpArticleSearchSerializer(serializers.ModelSerializer):
    """Serializer for search results."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    
    class Meta:
        model = HelpArticle
        fields = [
            'id', 'title', 'slug', 'summary',
            'category_name', 'category_slug',
            'view_count', 'published_at'
        ]


class HelpArticleFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for submitting feedback."""
    
    class Meta:
        model = HelpArticleFeedback
        fields = ['article', 'is_helpful', 'comment']
    
    def create(self, validated_data):
        request = self.context.get('request')
        
        # Add user if authenticated
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        # Add session ID for anonymous users
        if request:
            validated_data['session_id'] = request.session.session_key or ''
        
        # Update article feedback counts
        article = validated_data['article']
        article.mark_helpful(validated_data['is_helpful'])
        
        return super().create(validated_data)


class PopularSearchSerializer(serializers.ModelSerializer):
    """Serializer for popular searches."""
    
    class Meta:
        model = PopularSearch
        fields = ['search_term', 'search_count']


# =============================================================================
# ADMIN SERIALIZERS
# =============================================================================

class HelpCategoryAdminSerializer(serializers.ModelSerializer):
    """Admin serializer for managing categories."""
    article_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = HelpCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'display_order', 'target_audience', 'is_active',
            'article_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class HelpArticleAdminSerializer(serializers.ModelSerializer):
    """Admin serializer for managing articles."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    helpfulness_score = serializers.FloatField(read_only=True)
    
    class Meta:
        model = HelpArticle
        fields = [
            'id', 'title', 'slug', 'summary', 'content', 'keywords',
            'category', 'category_name',
            'target_audience', 'display_order',
            'status', 'published_at',
            'view_count', 'helpful_count', 'not_helpful_count', 'helpfulness_score',
            'related_articles',
            'version', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'view_count', 'helpful_count', 'not_helpful_count',
            'version', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        request = self.context.get('request')
        related = validated_data.pop('related_articles', [])
        
        if request and request.user:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user
        
        article = super().create(validated_data)
        
        if related:
            article.related_articles.set(related)
        
        return article
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        related = validated_data.pop('related_articles', None)
        
        if request and request.user:
            validated_data['updated_by'] = request.user
        
        # Increment version on content changes
        if 'content' in validated_data or 'title' in validated_data:
            validated_data['version'] = instance.version + 1
        
        article = super().update(instance, validated_data)
        
        if related is not None:
            article.related_articles.set(related)
        
        return article
