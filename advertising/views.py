"""
Advertising Views

Phase 1 Implementation:
- Farmer-facing: Get relevant partner offers
- Public: Submit advertiser leads
- Admin: Manage partners, offers, and leads
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import Q, Sum

from .models import Partner, PartnerOffer, OfferInteraction, AdvertiserLead, TargetingCriteria
from .serializers import (
    PartnerSerializer, PartnerListSerializer,
    PartnerOfferSerializer, FarmerOfferSerializer,
    OfferClickSerializer,
    AdvertiserLeadSerializer, AdvertiserLeadCreateSerializer,
    PartnerOfferAnalyticsSerializer,
)


# =============================================================================
# FARMER-FACING VIEWS
# =============================================================================

class FarmerOffersView(APIView):
    """
    GET /api/advertising/offers/
    
    Get relevant partner offers for the authenticated farmer.
    Filters based on targeting criteria and farmer profile.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        farm = getattr(request.user, 'farm', None)
        if not farm:
            return Response(
                {'error': 'No farm associated with this account', 'code': 'NO_FARM'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Base queryset: active offers within date range
        now = timezone.now()
        offers = PartnerOffer.objects.filter(
            is_active=True,
            partner__is_active=True,
            start_date__lte=now,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        
        # Apply targeting filters
        offers = self._apply_targeting(offers, farm)
        
        # Order by featured first, then priority
        offers = offers.order_by('-is_featured', '-priority', '-created_at')[:10]
        
        # Record impressions
        for offer in offers:
            # Check if farmer already saw this today (avoid duplicate impressions)
            today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            existing = OfferInteraction.objects.filter(
                offer=offer,
                farm=farm,
                interaction_type='impression',
                created_at__gte=today_start
            ).exists()
            
            if not existing:
                offer.record_impression()
                OfferInteraction.objects.create(
                    offer=offer,
                    farm=farm,
                    interaction_type='impression',
                    source_page=request.query_params.get('source', 'dashboard')
                )
        
        serializer = FarmerOfferSerializer(offers, many=True)
        return Response({
            'offers': serializer.data,
            'count': len(serializer.data),
        })
    
    def _apply_targeting(self, offers, farm):
        """Filter offers based on targeting criteria and farm attributes"""
        # Get farm attributes
        farm_region = getattr(farm, 'region', None)
        farm_flock_size = getattr(farm, 'total_birds', 0) or 0
        farm_experience = getattr(farm, 'experience_level', None)
        has_marketplace = getattr(farm, 'has_marketplace_access', False)
        is_government = getattr(farm, 'is_government_farmer', False)
        
        # Build filter
        q_filter = Q(targeting=TargetingCriteria.ALL_FARMERS)
        
        # Region targeting
        if farm_region:
            q_filter |= Q(
                targeting=TargetingCriteria.BY_REGION,
                target_regions__contains=[farm_region]
            )
        
        # Flock size targeting
        q_filter |= Q(
            targeting=TargetingCriteria.BY_FLOCK_SIZE,
            min_flock_size__lte=farm_flock_size,
        ) & (
            Q(max_flock_size__isnull=True) | Q(max_flock_size__gte=farm_flock_size)
        )
        
        # Marketplace active targeting
        if has_marketplace:
            q_filter |= Q(targeting=TargetingCriteria.MARKETPLACE_ACTIVE)
        
        # Government program targeting
        if is_government:
            q_filter |= Q(targeting=TargetingCriteria.GOVERNMENT_FARMERS)
        
        return offers.filter(q_filter)


class OfferClickView(APIView):
    """
    POST /api/advertising/offers/click/
    
    Record when a farmer clicks on an offer.
    Call this when redirecting to the offer URL.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = OfferClickSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        farm = getattr(request.user, 'farm', None)
        if not farm:
            return Response(
                {'error': 'No farm associated with this account', 'code': 'NO_FARM'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            offer = PartnerOffer.objects.get(id=serializer.validated_data['offer_id'])
        except PartnerOffer.DoesNotExist:
            return Response(
                {'error': 'Offer not found', 'code': 'OFFER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Record click
        offer.record_click()
        OfferInteraction.objects.create(
            offer=offer,
            farm=farm,
            interaction_type='click',
            source_page=serializer.validated_data.get('source_page', 'dashboard')
        )
        
        return Response({
            'success': True,
            'redirect_url': offer.cta_url,
        })


class DismissOfferView(APIView):
    """
    POST /api/advertising/offers/{id}/dismiss/
    
    Record when a farmer dismisses an offer.
    Can be used to avoid showing it again.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, offer_id):
        farm = getattr(request.user, 'farm', None)
        if not farm:
            return Response(
                {'error': 'No farm associated with this account', 'code': 'NO_FARM'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            offer = PartnerOffer.objects.get(id=offer_id)
        except PartnerOffer.DoesNotExist:
            return Response(
                {'error': 'Offer not found', 'code': 'OFFER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        OfferInteraction.objects.create(
            offer=offer,
            farm=farm,
            interaction_type='dismissed',
            source_page=request.data.get('source_page', 'dashboard')
        )
        
        return Response({'success': True})


# =============================================================================
# PUBLIC VIEWS
# =============================================================================

class AdvertiseWithUsView(APIView):
    """
    GET /api/public/advertise/
    POST /api/public/advertise/
    
    Public endpoint for advertiser lead capture.
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Return advertising info and categories"""
        from .models import PartnerCategory
        
        return Response({
            'title': 'Advertise on YEA Poultry Platform',
            'description': 'Reach thousands of verified poultry farmers across Ghana',
            'benefits': [
                'Direct access to verified, active poultry farmers',
                'Target by region, flock size, or production volume',
                'Farmers with transaction history and production data',
                'Premium placement on farmer dashboards',
                'Detailed analytics and reporting',
            ],
            'categories': [
                {'value': choice[0], 'label': choice[1]}
                for choice in PartnerCategory.choices
            ],
            'budget_ranges': [
                {'value': 'under_500', 'label': 'Under GHS 500/month'},
                {'value': '500_2000', 'label': 'GHS 500 - 2,000/month'},
                {'value': '2000_5000', 'label': 'GHS 2,000 - 5,000/month'},
                {'value': 'over_5000', 'label': 'Over GHS 5,000/month'},
                {'value': 'not_sure', 'label': 'Not Sure Yet'},
            ],
            'platform_stats': self._get_platform_stats(),
        })
    
    def post(self, request):
        """Submit an advertiser lead"""
        serializer = AdvertiserLeadCreateSerializer(data=request.data)
        if serializer.is_valid():
            lead = serializer.save()
            
            # TODO: Send notification to admin (use Celery task)
            # from core.tasks import send_admin_notification
            # send_admin_notification.delay('new_advertiser_lead', lead.id)
            
            return Response({
                'success': True,
                'message': 'Thank you for your interest! Our team will contact you within 2 business days.',
                'lead_id': str(lead.id),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_platform_stats(self):
        """Return platform stats to show advertisers"""
        from farms.models import Farm
        from sales_revenue.models import Order
        
        try:
            total_farmers = Farm.objects.filter(application_status='Approved').count()
            active_farmers = Farm.objects.filter(
                application_status='Approved',
                farm_status='Active'
            ).count()
            regions = Farm.objects.filter(
                application_status='Approved'
            ).values('region').distinct().count()
            
            return {
                'total_farmers': total_farmers,
                'active_farmers': active_farmers,
                'regions_covered': regions,
            }
        except Exception:
            # Return placeholder stats if error
            return {
                'total_farmers': '1000+',
                'active_farmers': '500+',
                'regions_covered': '16',
            }


# =============================================================================
# ADMIN VIEWS
# =============================================================================

class AdminPartnerListView(generics.ListCreateAPIView):
    """
    GET /api/admin/advertising/partners/
    POST /api/admin/advertising/partners/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PartnerSerializer
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Partner.objects.none()
        return Partner.objects.all()
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminPartnerDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/admin/advertising/partners/{id}/
    PUT /api/admin/advertising/partners/{id}/
    DELETE /api/admin/advertising/partners/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PartnerSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Partner.objects.none()
        return Partner.objects.all()


class AdminOfferListView(generics.ListCreateAPIView):
    """
    GET /api/admin/advertising/offers/
    POST /api/admin/advertising/offers/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PartnerOfferSerializer
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return PartnerOffer.objects.none()
        
        queryset = PartnerOffer.objects.select_related('partner').all()
        
        # Filter by partner
        partner_id = self.request.query_params.get('partner')
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        
        # Filter by status
        active_only = self.request.query_params.get('active')
        if active_only == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                is_active=True,
                start_date__lte=now,
            ).filter(
                Q(end_date__isnull=True) | Q(end_date__gte=now)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AdminOfferDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/admin/advertising/offers/{id}/
    PUT /api/admin/advertising/offers/{id}/
    DELETE /api/admin/advertising/offers/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PartnerOfferSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return PartnerOffer.objects.none()
        return PartnerOffer.objects.select_related('partner').all()


class AdminLeadListView(generics.ListAPIView):
    """
    GET /api/admin/advertising/leads/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AdvertiserLeadSerializer
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return AdvertiserLead.objects.none()
        
        queryset = AdvertiserLead.objects.all()
        
        # Filter by status
        lead_status = self.request.query_params.get('status')
        if lead_status:
            queryset = queryset.filter(status=lead_status)
        
        return queryset


class AdminLeadDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/admin/advertising/leads/{id}/
    PUT /api/admin/advertising/leads/{id}/
    PATCH /api/admin/advertising/leads/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AdvertiserLeadSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return AdvertiserLead.objects.none()
        return AdvertiserLead.objects.all()


class AdminOfferAnalyticsView(APIView):
    """
    GET /api/admin/advertising/analytics/
    
    Get advertising analytics summary.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Admin access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Overall stats
        total_partners = Partner.objects.filter(is_active=True).count()
        verified_partners = Partner.objects.filter(is_active=True, is_verified=True).count()
        
        now = timezone.now()
        active_offers = PartnerOffer.objects.filter(
            is_active=True,
            start_date__lte=now,
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        ).count()
        
        # Aggregate impressions and clicks
        totals = PartnerOffer.objects.aggregate(
            total_impressions=Sum('impressions'),
            total_clicks=Sum('clicks'),
        )
        
        # Lead stats
        new_leads = AdvertiserLead.objects.filter(status='new').count()
        total_leads = AdvertiserLead.objects.count()
        converted_leads = AdvertiserLead.objects.filter(status='converted').count()
        
        # Top performing offers
        top_offers = PartnerOffer.objects.filter(
            impressions__gt=0
        ).order_by('-clicks')[:5]
        
        return Response({
            'partners': {
                'total': total_partners,
                'verified': verified_partners,
            },
            'offers': {
                'active': active_offers,
                'total_impressions': totals['total_impressions'] or 0,
                'total_clicks': totals['total_clicks'] or 0,
            },
            'leads': {
                'new': new_leads,
                'total': total_leads,
                'converted': converted_leads,
                'conversion_rate': f"{(converted_leads / total_leads * 100):.1f}%" if total_leads > 0 else "0%",
            },
            'top_offers': PartnerOfferAnalyticsSerializer(top_offers, many=True).data,
        })
