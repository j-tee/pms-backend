"""
Help Files Views

Public API endpoints for the help/knowledge base system.
All public endpoints are accessible without authentication.
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404

from .help_models import HelpCategory, HelpArticle, HelpArticleFeedback, PopularSearch
from .help_serializers import (
    HelpCategoryListSerializer,
    HelpCategoryDetailSerializer,
    HelpArticleListSerializer,
    HelpArticleDetailSerializer,
    HelpArticleSearchSerializer,
    HelpArticleFeedbackSerializer,
    PopularSearchSerializer,
)


# =============================================================================
# PUBLIC VIEWS (No Authentication Required)
# =============================================================================

class HelpCategoryListView(generics.ListAPIView):
    """
    GET /api/public/help/categories/
    
    List all active help categories with article counts.
    Public access - no authentication required.
    
    Query Parameters:
    - audience: Filter by target audience (all, farmers, buyers, staff)
    """
    permission_classes = [AllowAny]
    serializer_class = HelpCategoryListSerializer
    
    def get_queryset(self):
        queryset = HelpCategory.objects.filter(is_active=True)
        
        # Filter by audience
        audience = self.request.query_params.get('audience')
        if audience and audience != 'all':
            queryset = queryset.filter(
                Q(target_audience='all') | Q(target_audience=audience)
            )
        
        return queryset.order_by('display_order', 'name')


class HelpCategoryDetailView(generics.RetrieveAPIView):
    """
    GET /api/public/help/categories/{slug}/
    
    Get a category with all its published articles.
    Public access - no authentication required.
    """
    permission_classes = [AllowAny]
    serializer_class = HelpCategoryDetailSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        return HelpCategory.objects.filter(is_active=True)


class HelpArticleListView(generics.ListAPIView):
    """
    GET /api/public/help/articles/
    
    List all published help articles.
    Public access - no authentication required.
    
    Query Parameters:
    - category: Filter by category slug
    - audience: Filter by target audience
    - sort: Sort by (popular, recent, title)
    """
    permission_classes = [AllowAny]
    serializer_class = HelpArticleListSerializer
    
    def get_queryset(self):
        queryset = HelpArticle.objects.filter(
            status='published',
            is_deleted=False
        ).select_related('category')
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Filter by audience
        audience = self.request.query_params.get('audience')
        if audience and audience != 'all':
            queryset = queryset.filter(
                Q(target_audience='all') | Q(target_audience=audience)
            )
        
        # Sorting
        sort = self.request.query_params.get('sort', 'order')
        if sort == 'popular':
            queryset = queryset.order_by('-view_count')
        elif sort == 'recent':
            queryset = queryset.order_by('-published_at')
        elif sort == 'title':
            queryset = queryset.order_by('title')
        else:
            queryset = queryset.order_by('category__display_order', 'display_order', 'title')
        
        return queryset


class HelpArticleDetailView(generics.RetrieveAPIView):
    """
    GET /api/public/help/articles/{slug}/
    
    Get a single help article by slug.
    Public access - no authentication required.
    Automatically increments view count.
    """
    permission_classes = [AllowAny]
    serializer_class = HelpArticleDetailSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        return HelpArticle.objects.filter(
            status='published',
            is_deleted=False
        ).select_related('category').prefetch_related('related_articles')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Increment view count
        instance.increment_view()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class HelpSearchView(APIView):
    """
    GET /api/public/help/search/
    
    Search help articles by keyword.
    Public access - no authentication required.
    
    Query Parameters:
    - q: Search query (required)
    - category: Filter by category slug
    - limit: Maximum results (default: 20)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'Search query is required', 'code': 'MISSING_QUERY'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(query) < 2:
            return Response(
                {'error': 'Search query must be at least 2 characters', 'code': 'QUERY_TOO_SHORT'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build search query
        queryset = HelpArticle.objects.filter(
            status='published',
            is_deleted=False
        ).filter(
            Q(title__icontains=query) |
            Q(summary__icontains=query) |
            Q(content__icontains=query) |
            Q(keywords__icontains=query)
        ).select_related('category')
        
        # Filter by category
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        # Order by relevance (title matches first, then summary, then content)
        queryset = queryset.annotate(
            title_match=Count('id', filter=Q(title__icontains=query)),
            summary_match=Count('id', filter=Q(summary__icontains=query)),
        ).order_by('-title_match', '-summary_match', '-view_count')
        
        # Limit results
        limit = min(int(request.query_params.get('limit', 20)), 50)
        results = queryset[:limit]
        
        # Record search for analytics
        PopularSearch.record_search(query, has_results=results.exists())
        
        serializer = HelpArticleSearchSerializer(results, many=True)
        
        return Response({
            'query': query,
            'count': len(serializer.data),
            'results': serializer.data
        })


class HelpFeedbackView(generics.CreateAPIView):
    """
    POST /api/public/help/feedback/
    
    Submit feedback on a help article.
    Public access - no authentication required.
    
    Request Body:
    {
        "article": "uuid",
        "is_helpful": true/false,
        "comment": "optional feedback comment"
    }
    """
    permission_classes = [AllowAny]
    serializer_class = HelpArticleFeedbackSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
            return Response({
                'message': 'Thank you for your feedback!',
                'is_helpful': serializer.validated_data['is_helpful']
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            # Handle duplicate feedback gracefully
            if 'unique' in str(e).lower():
                return Response({
                    'message': 'You have already submitted feedback for this article.',
                    'code': 'DUPLICATE_FEEDBACK'
                }, status=status.HTTP_409_CONFLICT)
            raise


class PopularArticlesView(generics.ListAPIView):
    """
    GET /api/public/help/popular/
    
    Get most viewed/popular help articles.
    Public access - no authentication required.
    
    Query Parameters:
    - limit: Maximum results (default: 10)
    """
    permission_classes = [AllowAny]
    serializer_class = HelpArticleListSerializer
    
    def get_queryset(self):
        limit = min(int(self.request.query_params.get('limit', 10)), 20)
        
        return HelpArticle.objects.filter(
            status='published',
            is_deleted=False
        ).select_related('category').order_by('-view_count')[:limit]


class PopularSearchesView(generics.ListAPIView):
    """
    GET /api/public/help/popular-searches/
    
    Get popular search terms.
    Useful for showing "Popular Topics" or search suggestions.
    Public access - no authentication required.
    
    Query Parameters:
    - limit: Maximum results (default: 10)
    """
    permission_classes = [AllowAny]
    serializer_class = PopularSearchSerializer
    
    def get_queryset(self):
        limit = min(int(self.request.query_params.get('limit', 10)), 20)
        
        return PopularSearch.objects.filter(
            has_results=True
        ).order_by('-search_count')[:limit]


class HelpOverviewView(APIView):
    """
    GET /api/public/help/
    
    Get help center overview with categories and featured articles.
    This is the main entry point for the help center.
    Public access - no authentication required.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get all active categories (article_count is a property on the model)
        categories = HelpCategory.objects.filter(is_active=True).order_by('display_order', 'name')
        
        # Get popular articles
        popular_articles = HelpArticle.objects.filter(
            status='published',
            is_deleted=False
        ).select_related('category').order_by('-view_count')[:5]
        
        # Get recent articles
        recent_articles = HelpArticle.objects.filter(
            status='published',
            is_deleted=False
        ).select_related('category').order_by('-published_at')[:5]
        
        # Get popular searches
        popular_searches = PopularSearch.objects.filter(
            has_results=True
        ).order_by('-search_count')[:10]
        
        # Total article count
        total_articles = HelpArticle.objects.filter(
            status='published',
            is_deleted=False
        ).count()
        
        return Response({
            'total_articles': total_articles,
            'categories': HelpCategoryListSerializer(categories, many=True).data,
            'popular_articles': HelpArticleListSerializer(popular_articles, many=True).data,
            'recent_articles': HelpArticleListSerializer(recent_articles, many=True).data,
            'popular_searches': PopularSearchSerializer(popular_searches, many=True).data,
        })
