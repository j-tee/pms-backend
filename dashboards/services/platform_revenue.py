"""
Platform Revenue Analytics Service (SUPER_ADMIN Only)

Provides platform monetization metrics:
- Advertising revenue (AdSense + Partners)
- Marketplace activation fees
- Partner payments tracking

Access Control: SUPER_ADMIN and YEA_OFFICIAL only
"""

from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncDate, Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class PlatformRevenueService:
    """
    Revenue analytics for platform owner (SUPER_ADMIN).
    This data is NOT visible to YEA administrators.
    """
    
    def __init__(self):
        self.now = timezone.now()
        self.today = self.now.date()
    
    def get_revenue_overview(self):
        """
        Get platform revenue overview.
        
        Returns:
            dict: Revenue metrics
        """
        from advertising.models import (
            PartnerOffer, OfferClick, OfferConversion,
            AdPartnerPayment, AdSenseEarning
        )
        from farms.models import Farm
        
        # Date ranges
        this_month_start = self.today.replace(day=1)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        # === ADVERTISING REVENUE ===
        
        # AdSense earnings this month
        adsense_this_month = AdSenseEarning.objects.filter(
            earning_date__gte=this_month_start
        ).aggregate(
            total=Coalesce(Sum('amount'), Decimal('0.00'))
        )['total']
        
        # Partner ad conversions this month
        partner_conversions = OfferConversion.objects.filter(
            converted_at__gte=this_month_start,
            is_valid=True
        ).aggregate(
            total_value=Coalesce(Sum('conversion_value'), Decimal('0.00')),
            count=Count('id')
        )
        
        # Partner payments due/paid
        partner_payments = AdPartnerPayment.objects.filter(
            created_at__gte=this_month_start
        ).aggregate(
            paid=Coalesce(
                Sum('amount', filter=Q(status='paid')),
                Decimal('0.00')
            ),
            pending=Coalesce(
                Sum('amount', filter=Q(status='pending')),
                Decimal('0.00')
            )
        )
        
        # === MARKETPLACE ACTIVATION FEES ===
        
        # Active marketplace subscriptions
        try:
            from subscriptions.models import Subscription
            active_subs = Subscription.objects.filter(
                is_active=True,
                end_date__gt=self.now
            )
            
            subscription_stats = active_subs.aggregate(
                count=Count('id'),
                monthly_revenue=Coalesce(Sum('plan__price_monthly'), Decimal('0.00'))
            )
        except Exception:
            subscription_stats = {'count': 0, 'monthly_revenue': Decimal('0.00')}
        
        # Farms with paid marketplace access
        paid_marketplace_farms = Farm.objects.filter(
            subscription_type__in=['standard', 'verified']
        ).count()
        
        subsidized_farms = Farm.objects.filter(
            subscription_type='government_subsidized'
        ).count()
        
        # === TOTALS ===
        
        total_ad_revenue = adsense_this_month + partner_conversions['total_value']
        # Assuming 20% commission on partner conversions
        platform_ad_commission = partner_conversions['total_value'] * Decimal('0.20')
        
        return {
            'advertising': {
                'adsense_this_month': float(adsense_this_month),
                'partner_conversions': partner_conversions['count'],
                'partner_conversion_value': float(partner_conversions['total_value']),
                'platform_commission': float(platform_ad_commission),
                'partner_payments_paid': float(partner_payments['paid']),
                'partner_payments_pending': float(partner_payments['pending'])
            },
            'marketplace_activation': {
                'paid_farms': paid_marketplace_farms,
                'subsidized_farms': subsidized_farms,
                'subscription_revenue': float(subscription_stats.get('monthly_revenue', 0))
            },
            'totals': {
                'ad_revenue_this_month': float(total_ad_revenue),
                'platform_fees_this_month': float(subscription_stats.get('monthly_revenue', 0)),
                'net_revenue_estimate': float(
                    platform_ad_commission + subscription_stats.get('monthly_revenue', Decimal('0'))
                )
            },
            'as_of': self.now.isoformat()
        }
    
    def get_revenue_trend(self, months=6):
        """
        Get monthly revenue trend.
        
        Args:
            months: Number of months to include
            
        Returns:
            list: Monthly revenue data
        """
        from advertising.models import AdSenseEarning, OfferConversion
        
        start_date = self.now - timedelta(days=months * 30)
        
        # AdSense by month
        adsense_trend = AdSenseEarning.objects.filter(
            earning_date__gte=start_date
        ).annotate(
            month=TruncMonth('earning_date')
        ).values('month').annotate(
            amount=Sum('amount')
        ).order_by('month')
        
        # Conversions by month
        conversion_trend = OfferConversion.objects.filter(
            converted_at__gte=start_date,
            is_valid=True
        ).annotate(
            month=TruncMonth('converted_at')
        ).values('month').annotate(
            amount=Sum('conversion_value'),
            count=Count('id')
        ).order_by('month')
        
        # Merge data
        monthly_data = {}
        
        for item in adsense_trend:
            month_key = item['month'].strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'adsense': 0, 'conversions': 0, 'conversion_count': 0}
            monthly_data[month_key]['adsense'] = float(item['amount'] or 0)
        
        for item in conversion_trend:
            month_key = item['month'].strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'adsense': 0, 'conversions': 0, 'conversion_count': 0}
            monthly_data[month_key]['conversions'] = float(item['amount'] or 0)
            monthly_data[month_key]['conversion_count'] = item['count']
        
        return [
            {
                'month': month,
                'adsense_revenue': data['adsense'],
                'conversion_revenue': data['conversions'],
                'conversion_count': data['conversion_count'],
                'total': data['adsense'] + data['conversions']
            }
            for month, data in sorted(monthly_data.items())
        ]
    
    def get_advertising_performance(self):
        """
        Get advertising performance metrics.
        
        Returns:
            dict: Ad performance data
        """
        from advertising.models import PartnerOffer, OfferClick, OfferConversion
        
        this_month_start = self.today.replace(day=1)
        
        # Active offers
        active_offers = PartnerOffer.objects.filter(
            status='active',
            start_date__lte=self.today,
            end_date__gte=self.today
        ).count()
        
        # Clicks and conversions this month
        clicks = OfferClick.objects.filter(
            clicked_at__gte=this_month_start
        ).count()
        
        conversions = OfferConversion.objects.filter(
            converted_at__gte=this_month_start,
            is_valid=True
        )
        
        conversion_stats = conversions.aggregate(
            count=Count('id'),
            total_value=Coalesce(Sum('conversion_value'), Decimal('0.00'))
        )
        
        # Conversion rate
        conversion_rate = 0
        if clicks > 0:
            conversion_rate = round((conversion_stats['count'] / clicks * 100), 2)
        
        # Top performing offers
        top_offers = OfferConversion.objects.filter(
            converted_at__gte=this_month_start,
            is_valid=True
        ).values(
            'offer_id', 'offer__title', 'offer__partner__company_name'
        ).annotate(
            conversions=Count('id'),
            revenue=Sum('conversion_value')
        ).order_by('-revenue')[:5]
        
        return {
            'summary': {
                'active_offers': active_offers,
                'clicks_this_month': clicks,
                'conversions_this_month': conversion_stats['count'],
                'conversion_rate': conversion_rate,
                'conversion_value': float(conversion_stats['total_value'])
            },
            'top_offers': [
                {
                    'offer_id': str(item['offer_id']),
                    'title': item['offer__title'],
                    'partner': item['offer__partner__company_name'],
                    'conversions': item['conversions'],
                    'revenue': float(item['revenue'] or 0)
                }
                for item in top_offers
            ]
        }
    
    def get_partner_payments(self, status=None):
        """
        Get partner payment tracking.
        
        Args:
            status: Filter by payment status
            
        Returns:
            list: Partner payments
        """
        from advertising.models import AdPartnerPayment
        
        payments = AdPartnerPayment.objects.all()
        
        if status:
            payments = payments.filter(status=status)
        
        payments = payments.select_related('partner').order_by('-created_at')[:50]
        
        return [
            {
                'id': str(p.id),
                'partner': p.partner.company_name,
                'amount': float(p.amount),
                'status': p.status,
                'payment_date': p.payment_date.isoformat() if p.payment_date else None,
                'created_at': p.created_at.isoformat()
            }
            for p in payments
        ]
    
    def get_marketplace_activation_stats(self):
        """
        Get marketplace activation (subscription) statistics.
        
        Returns:
            dict: Activation stats
        """
        from farms.models import Farm
        from sales_revenue.models import PlatformSettings
        
        # Get current settings
        try:
            settings = PlatformSettings.get_settings()
            activation_fee = float(settings.marketplace_activation_fee)
        except Exception:
            activation_fee = 50.00  # Default
        
        # Farm subscription breakdown
        subscription_breakdown = Farm.objects.values('subscription_type').annotate(
            count=Count('id')
        )
        
        breakdown = {item['subscription_type']: item['count'] for item in subscription_breakdown}
        
        # Calculate potential revenue
        paid_farms = breakdown.get('standard', 0) + breakdown.get('verified', 0)
        potential_monthly_revenue = paid_farms * activation_fee
        
        return {
            'breakdown': {
                'none': breakdown.get('none', 0),
                'government_subsidized': breakdown.get('government_subsidized', 0),
                'standard': breakdown.get('standard', 0),
                'verified': breakdown.get('verified', 0)
            },
            'pricing': {
                'activation_fee_ghs': activation_fee
            },
            'revenue': {
                'paying_farms': paid_farms,
                'potential_monthly_ghs': potential_monthly_revenue
            }
        }
