"""
Help Files Admin Views

Admin endpoints for managing help categories and articles.
Only accessible by SUPER_ADMIN.
"""
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count

from .help_models import HelpCategory, HelpArticle, HelpArticleFeedback, PopularSearch
from .help_serializers import (
    HelpCategoryAdminSerializer,
    HelpArticleAdminSerializer,
    HelpArticleFeedbackSerializer,
    PopularSearchSerializer,
)
from .permissions import IsSuperAdminOnly


class HelpCategoryAdminViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD for help categories.
    Only SUPER_ADMIN can access.
    """
    permission_classes = [IsAuthenticated, IsSuperAdminOnly]
    serializer_class = HelpCategoryAdminSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        return HelpCategory.objects.annotate(
            article_count=Count(
                'articles',
                filter=Q(articles__is_deleted=False)
            )
        ).order_by('display_order', 'name')
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, id=None):
        """Toggle category active status."""
        category = self.get_object()
        category.is_active = not category.is_active
        category.save(update_fields=['is_active', 'updated_at'])
        
        return Response({
            'message': f"Category {'activated' if category.is_active else 'deactivated'}",
            'is_active': category.is_active
        })


class HelpArticleAdminViewSet(viewsets.ModelViewSet):
    """
    Admin CRUD for help articles.
    Only SUPER_ADMIN can access.
    """
    permission_classes = [IsAuthenticated, IsSuperAdminOnly]
    serializer_class = HelpArticleAdminSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        queryset = HelpArticle.objects.filter(
            is_deleted=False
        ).select_related('category')
        
        # Filter by status
        article_status = self.request.query_params.get('status')
        if article_status:
            queryset = queryset.filter(status=article_status)
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(summary__icontains=search) |
                Q(keywords__icontains=search)
            )
        
        return queryset.order_by('-updated_at')
    
    @action(detail=True, methods=['post'])
    def publish(self, request, id=None):
        """Publish an article."""
        article = self.get_object()
        article.publish(request.user)
        
        return Response({
            'message': 'Article published successfully',
            'status': article.status,
            'published_at': article.published_at
        })
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, id=None):
        """Unpublish an article (revert to draft)."""
        article = self.get_object()
        article.unpublish(request.user)
        
        return Response({
            'message': 'Article unpublished',
            'status': article.status
        })
    
    @action(detail=True, methods=['post'])
    def archive(self, request, id=None):
        """Archive an article."""
        article = self.get_object()
        article.archive(request.user)
        
        return Response({
            'message': 'Article archived',
            'status': article.status
        })
    
    @action(detail=True, methods=['get'])
    def feedback(self, request, id=None):
        """Get feedback for an article."""
        article = self.get_object()
        feedback = article.feedback.all().order_by('-created_at')[:50]
        
        return Response({
            'article_id': str(article.id),
            'article_title': article.title,
            'helpful_count': article.helpful_count,
            'not_helpful_count': article.not_helpful_count,
            'helpfulness_score': article.helpfulness_score,
            'feedback': HelpArticleFeedbackSerializer(feedback, many=True).data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete an article."""
        article = self.get_object()
        article.soft_delete(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class HelpAnalyticsView(generics.GenericAPIView):
    """
    GET /api/cms/help/analytics/
    
    Get help center analytics and insights.
    Only SUPER_ADMIN can access.
    """
    permission_classes = [IsAuthenticated, IsSuperAdminOnly]
    
    def get(self, request):
        # Article stats
        total_articles = HelpArticle.objects.filter(is_deleted=False).count()
        published_articles = HelpArticle.objects.filter(
            status='published', is_deleted=False
        ).count()
        draft_articles = HelpArticle.objects.filter(
            status='draft', is_deleted=False
        ).count()
        
        # View stats
        total_views = HelpArticle.objects.filter(
            is_deleted=False
        ).aggregate(total=Count('view_count'))['total'] or 0
        
        # Most viewed articles
        most_viewed = HelpArticle.objects.filter(
            status='published', is_deleted=False
        ).order_by('-view_count')[:10]
        
        # Least helpful articles (need improvement)
        needs_improvement = HelpArticle.objects.filter(
            status='published',
            is_deleted=False,
            not_helpful_count__gt=0
        ).annotate(
            helpfulness=Count('helpful_count') * 100 / (Count('helpful_count') + Count('not_helpful_count'))
        ).order_by('helpfulness')[:10]
        
        # Popular searches without results
        failed_searches = PopularSearch.objects.filter(
            has_results=False
        ).order_by('-search_count')[:10]
        
        # Category stats
        category_stats = HelpCategory.objects.annotate(
            article_count=Count('articles', filter=Q(articles__is_deleted=False)),
            published_count=Count('articles', filter=Q(articles__status='published', articles__is_deleted=False)),
        ).values('name', 'article_count', 'published_count')
        
        return Response({
            'summary': {
                'total_articles': total_articles,
                'published_articles': published_articles,
                'draft_articles': draft_articles,
                'total_views': total_views,
            },
            'most_viewed': [
                {
                    'id': str(a.id),
                    'title': a.title,
                    'view_count': a.view_count,
                    'helpfulness_score': a.helpfulness_score
                }
                for a in most_viewed
            ],
            'needs_improvement': [
                {
                    'id': str(a.id),
                    'title': a.title,
                    'helpful_count': a.helpful_count,
                    'not_helpful_count': a.not_helpful_count,
                    'helpfulness_score': a.helpfulness_score
                }
                for a in needs_improvement
            ],
            'failed_searches': PopularSearchSerializer(failed_searches, many=True).data,
            'category_stats': list(category_stats),
        })
