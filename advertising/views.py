"""
Advertising Views

Phase 1 Implementation:
- Farmer-facing: Get relevant partner offers with A/B testing
- Public: Submit advertiser leads
- Admin: Manage partners, offers, leads, payments, and conversions
"""

import random
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db import models as db_models
from django.db.models import Q, Sum, Count, Avg, F
from django.db.models.functions import TruncDate, TruncMonth

from .models import (
    Partner, PartnerOffer, OfferInteraction, AdvertiserLead,
    TargetingCriteria, OfferVariant, ConversionEvent, PartnerPayment,
    ConversionWebhookKey
)
from .serializers import (
    PartnerSerializer, PartnerListSerializer,
    PartnerOfferSerializer, FarmerOfferSerializer,
    OfferClickSerializer,
    AdvertiserLeadSerializer, AdvertiserLeadCreateSerializer,
    PartnerOfferAnalyticsSerializer,
    OfferVariantSerializer, OfferVariantListSerializer,
    ConversionEventSerializer, ConversionEventCreateSerializer, WebhookConversionSerializer,
    PartnerPaymentSerializer, PartnerPaymentCreateSerializer,
    WebhookKeySerializer,
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


# =============================================================================
# A/B TESTING VIEWS
# =============================================================================

class AdminOfferVariantListView(generics.ListCreateAPIView):
    """
    GET /api/admin/advertising/offers/{offer_id}/variants/
    POST /api/admin/advertising/offers/{offer_id}/variants/
    
    List or create variants for an offer (A/B testing)
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OfferVariantSerializer
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return OfferVariant.objects.none()
        offer_id = self.kwargs.get('offer_id')
        return OfferVariant.objects.filter(offer_id=offer_id)
    
    def perform_create(self, serializer):
        offer_id = self.kwargs.get('offer_id')
        offer = PartnerOffer.objects.get(id=offer_id)
        serializer.save(offer=offer)


class AdminOfferVariantDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/admin/advertising/variants/{id}/
    PUT /api/admin/advertising/variants/{id}/
    DELETE /api/admin/advertising/variants/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = OfferVariantSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return OfferVariant.objects.none()
        return OfferVariant.objects.all()


class AdminABTestResultsView(APIView):
    """
    GET /api/admin/advertising/offers/{offer_id}/ab-results/
    
    Get A/B testing results for an offer
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, offer_id):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Admin access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            offer = PartnerOffer.objects.get(id=offer_id)
        except PartnerOffer.DoesNotExist:
            return Response(
                {'error': 'Offer not found', 'code': 'OFFER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        variants = offer.variants.filter(is_active=True)
        
        # Calculate stats for each variant
        variant_stats = []
        best_ctr = 0
        best_cvr = 0
        best_ctr_variant = None
        best_cvr_variant = None
        
        for variant in variants:
            ctr = float(variant.click_through_rate)
            cvr = float(variant.conversion_rate)
            
            if ctr > best_ctr:
                best_ctr = ctr
                best_ctr_variant = variant.id
            
            if cvr > best_cvr:
                best_cvr = cvr
                best_cvr_variant = variant.id
            
            variant_stats.append({
                'id': str(variant.id),
                'name': variant.name,
                'traffic_percentage': variant.traffic_percentage,
                'impressions': variant.impressions,
                'clicks': variant.clicks,
                'conversions': variant.conversions,
                'ctr': f"{ctr:.2f}%",
                'cvr': f"{cvr:.2f}%",
                'is_winner': variant.is_winner,
            })
        
        # Also include base offer stats (if no variants, this is the "control")
        base_stats = {
            'id': 'base',
            'name': 'Original (No Variant)',
            'impressions': offer.impressions,
            'clicks': offer.clicks,
            'ctr': f"{float(offer.click_through_rate):.2f}%",
        }
        
        return Response({
            'offer_id': str(offer.id),
            'offer_title': offer.title,
            'is_ab_test_active': variants.count() > 0,
            'variants': variant_stats,
            'base_offer': base_stats,
            'recommendations': {
                'best_ctr_variant': str(best_ctr_variant) if best_ctr_variant else None,
                'best_cvr_variant': str(best_cvr_variant) if best_cvr_variant else None,
                'statistical_significance': self._calculate_significance(variant_stats),
            }
        })
    
    def _calculate_significance(self, variants):
        """Simple significance check (needs more data for proper statistical testing)"""
        if len(variants) < 2:
            return 'Need at least 2 variants for comparison'
        
        total_impressions = sum(v['impressions'] for v in variants)
        if total_impressions < 1000:
            return f'Need more data ({total_impressions}/1000 impressions)'
        
        return 'Sufficient data for analysis'


# =============================================================================
# CONVERSION TRACKING VIEWS
# =============================================================================

class AdminConversionListView(generics.ListCreateAPIView):
    """
    GET /api/admin/advertising/conversions/
    POST /api/admin/advertising/conversions/
    
    List all conversions or create manual conversion
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ConversionEventCreateSerializer
        return ConversionEventSerializer
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return ConversionEvent.objects.none()
        
        queryset = ConversionEvent.objects.select_related(
            'offer', 'offer__partner', 'farm', 'variant'
        ).all()
        
        # Filters
        offer_id = self.request.query_params.get('offer')
        if offer_id:
            queryset = queryset.filter(offer_id=offer_id)
        
        partner_id = self.request.query_params.get('partner')
        if partner_id:
            queryset = queryset.filter(offer__partner_id=partner_id)
        
        verified = self.request.query_params.get('verified')
        if verified == 'true':
            queryset = queryset.filter(is_verified=True)
        elif verified == 'false':
            queryset = queryset.filter(is_verified=False)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(source='manual')


class AdminConversionDetailView(generics.RetrieveUpdateAPIView):
    """
    GET /api/admin/advertising/conversions/{id}/
    PUT /api/admin/advertising/conversions/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ConversionEventSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return ConversionEvent.objects.none()
        return ConversionEvent.objects.select_related('offer', 'farm', 'variant').all()


class AdminVerifyConversionView(APIView):
    """
    POST /api/admin/advertising/conversions/{id}/verify/
    
    Verify a conversion
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Admin access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            conversion = ConversionEvent.objects.get(id=id)
        except ConversionEvent.DoesNotExist:
            return Response(
                {'error': 'Conversion not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        conversion.is_verified = True
        conversion.verified_by = request.user
        conversion.verified_at = timezone.now()
        conversion.save(update_fields=['is_verified', 'verified_by', 'verified_at'])
        
        # Update variant conversion count if applicable
        if conversion.variant:
            OfferVariant.objects.filter(pk=conversion.variant_id).update(
                conversions=F('conversions') + 1
            )
        
        return Response({
            'success': True,
            'message': 'Conversion verified successfully',
        })


class ConversionWebhookView(APIView):
    """
    POST /api/advertising/webhook/conversion/
    
    Endpoint for partners to send conversion data.
    Requires API key authentication.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        # Authenticate via API key
        api_key = request.headers.get('X-API-Key') or request.data.get('api_key')
        if not api_key:
            return Response(
                {'error': 'API key required', 'code': 'AUTH_REQUIRED'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            webhook_key = ConversionWebhookKey.objects.select_related('partner').get(
                api_key=api_key,
                is_active=True
            )
        except ConversionWebhookKey.DoesNotExist:
            return Response(
                {'error': 'Invalid API key', 'code': 'INVALID_KEY'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Update usage stats
        webhook_key.last_used_at = timezone.now()
        webhook_key.total_requests += 1
        webhook_key.save(update_fields=['last_used_at', 'total_requests'])
        
        # Validate data
        serializer = WebhookConversionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Verify offer belongs to this partner
        try:
            offer = PartnerOffer.objects.get(
                id=data['offer_id'],
                partner=webhook_key.partner
            )
        except PartnerOffer.DoesNotExist:
            return Response(
                {'error': 'Offer not found or does not belong to partner', 'code': 'OFFER_NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Try to find the farm by phone or email
        farm = None
        if data.get('farmer_phone') or data.get('farmer_email'):
            from farms.models import Farm
            from accounts.models import User
            
            user_filter = Q()
            if data.get('farmer_phone'):
                user_filter |= Q(phone_number=data['farmer_phone'])
            if data.get('farmer_email'):
                user_filter |= Q(email=data['farmer_email'])
            
            try:
                user = User.objects.filter(user_filter).first()
                if user:
                    farm = getattr(user, 'farm', None)
            except Exception:
                pass
        
        # Create conversion event
        conversion = ConversionEvent.objects.create(
            offer=offer,
            farm=farm,
            conversion_type=data['conversion_type'],
            conversion_value=data.get('conversion_value'),
            promo_code_used=data.get('promo_code', ''),
            external_reference=data.get('external_reference', ''),
            source='webhook',
        )
        
        return Response({
            'success': True,
            'conversion_id': str(conversion.id),
            'message': 'Conversion recorded successfully',
        }, status=status.HTTP_201_CREATED)


# =============================================================================
# PARTNER PAYMENT VIEWS
# =============================================================================

class AdminPartnerPaymentListView(generics.ListCreateAPIView):
    """
    GET /api/admin/advertising/payments/
    POST /api/admin/advertising/payments/
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PartnerPaymentCreateSerializer
        return PartnerPaymentSerializer
    
    def get_queryset(self):
        # Only SUPER_ADMIN can see partner payment revenue
        if self.request.user.role != 'SUPER_ADMIN':
            return PartnerPayment.objects.none()
        
        queryset = PartnerPayment.objects.select_related('partner', 'recorded_by').all()
        
        # Filters
        partner_id = self.request.query_params.get('partner')
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        
        payment_status = self.request.query_params.get('status')
        if payment_status:
            queryset = queryset.filter(status=payment_status)
        
        return queryset
    
    def perform_create(self, serializer):
        payment = serializer.save(recorded_by=self.request.user)
        # If status is paid and paid_at not set, set it now
        if payment.status == 'paid' and not payment.paid_at:
            payment.paid_at = timezone.now()
            payment.save(update_fields=['paid_at'])


class AdminPartnerPaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/admin/advertising/payments/{id}/
    PUT /api/admin/advertising/payments/{id}/
    DELETE /api/admin/advertising/payments/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PartnerPaymentSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        if self.request.user.role != 'SUPER_ADMIN':
            return PartnerPayment.objects.none()
        return PartnerPayment.objects.select_related('partner', 'recorded_by').all()


class AdminMarkPaymentPaidView(APIView):
    """
    POST /api/admin/advertising/payments/{id}/mark-paid/
    
    Mark a payment as paid
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        if request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Admin access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            payment = PartnerPayment.objects.get(id=id)
        except PartnerPayment.DoesNotExist:
            return Response(
                {'error': 'Payment not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        reference = request.data.get('transaction_reference', '')
        payment.mark_as_paid(user=request.user, reference=reference)
        
        return Response({
            'success': True,
            'message': 'Payment marked as paid',
            'paid_at': payment.paid_at.isoformat(),
        })


class AdminWebhookKeyListView(generics.ListCreateAPIView):
    """
    GET /api/admin/advertising/webhook-keys/
    POST /api/admin/advertising/webhook-keys/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WebhookKeySerializer
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return ConversionWebhookKey.objects.none()
        return ConversionWebhookKey.objects.select_related('partner').all()


class AdminWebhookKeyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET /api/admin/advertising/webhook-keys/{id}/
    PUT /api/admin/advertising/webhook-keys/{id}/
    DELETE /api/admin/advertising/webhook-keys/{id}/
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WebhookKeySerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        if self.request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return ConversionWebhookKey.objects.none()
        return ConversionWebhookKey.objects.all()


class AdminRegenerateWebhookKeyView(APIView):
    """
    POST /api/admin/advertising/webhook-keys/{id}/regenerate/
    
    Regenerate a webhook API key
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, id):
        if request.user.role not in ['SUPER_ADMIN', 'YEA_OFFICIAL']:
            return Response(
                {'error': 'Admin access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            webhook_key = ConversionWebhookKey.objects.get(id=id)
        except ConversionWebhookKey.DoesNotExist:
            return Response(
                {'error': 'Webhook key not found', 'code': 'NOT_FOUND'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        new_key = webhook_key.regenerate_key()
        
        return Response({
            'success': True,
            'message': 'API key regenerated successfully',
            'api_key': new_key,
        })


class AdminAdvertisingRevenueView(APIView):
    """
    GET /api/admin/advertising/revenue/
    
    Get advertising revenue summary (SUPER_ADMIN only)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if request.user.role != 'SUPER_ADMIN':
            return Response(
                {'error': 'Super admin access required', 'code': 'PERMISSION_DENIED'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        now = timezone.now()
        today = now.date()
        this_month_start = today.replace(day=1)
        last_month_start = (this_month_start - timezone.timedelta(days=1)).replace(day=1)
        this_year_start = today.replace(month=1, day=1)
        
        # Payment stats
        paid_payments = PartnerPayment.objects.filter(status='paid')
        
        # Total revenue
        total_revenue = paid_payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # This month
        this_month_revenue = paid_payments.filter(
            paid_at__date__gte=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Last month
        last_month_revenue = paid_payments.filter(
            paid_at__date__gte=last_month_start,
            paid_at__date__lt=this_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # This year
        this_year_revenue = paid_payments.filter(
            paid_at__date__gte=this_year_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Pending payments
        pending = PartnerPayment.objects.filter(status='pending')
        pending_amount = pending.aggregate(total=Sum('amount'))['total'] or 0
        pending_count = pending.count()
        
        # Overdue payments
        overdue = PartnerPayment.objects.filter(
            status='pending',
            due_date__lt=today
        )
        overdue_amount = overdue.aggregate(total=Sum('amount'))['total'] or 0
        overdue_count = overdue.count()
        
        # Monthly breakdown (last 12 months)
        monthly_data = paid_payments.filter(
            paid_at__date__gte=today - timezone.timedelta(days=365)
        ).annotate(
            month=TruncMonth('paid_at')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        # Revenue by partner
        by_partner = paid_payments.values(
            'partner__company_name'
        ).annotate(
            total=Sum('amount'),
            payments=Count('id')
        ).order_by('-total')[:10]
        
        # Growth calculation
        if last_month_revenue > 0:
            growth = ((this_month_revenue - last_month_revenue) / last_month_revenue) * 100
        else:
            growth = 100 if this_month_revenue > 0 else 0
        
        return Response({
            'total_revenue': f"{total_revenue:.2f}",
            'this_month': f"{this_month_revenue:.2f}",
            'last_month': f"{last_month_revenue:.2f}",
            'this_year': f"{this_year_revenue:.2f}",
            'growth_percentage': f"{growth:.1f}",
            'pending': {
                'amount': f"{pending_amount:.2f}",
                'count': pending_count,
            },
            'overdue': {
                'amount': f"{overdue_amount:.2f}",
                'count': overdue_count,
            },
            'monthly_breakdown': [
                {
                    'month': item['month'].strftime('%Y-%m'),
                    'amount': f"{item['total']:.2f}",
                    'payments': item['count'],
                }
                for item in monthly_data
            ],
            'top_partners': [
                {
                    'partner_name': item['partner__company_name'],
                    'total_revenue': f"{item['total']:.2f}",
                    'payments': item['payments'],
                }
                for item in by_partner
            ],
        })
