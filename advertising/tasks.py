"""
Advertising Celery tasks for YEA Poultry Management System.

Background tasks for advertising analytics, partner management,
lead processing, and payment operations.
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count, Avg, F
from django.core.cache import cache
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def aggregate_advertising_analytics():
    """
    Aggregate advertising performance metrics.
    
    Caches daily analytics for dashboard performance.
    """
    from advertising.models import OfferInteraction, PartnerOffer, Partner
    
    logger.info("Aggregating advertising analytics...")
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=7)
    month_start = today.replace(day=1)
    
    # Daily metrics
    daily_interactions = OfferInteraction.objects.filter(
        timestamp__date=yesterday
    ).aggregate(
        impressions=Count('id', filter=F('interaction_type') == 'impression'),
        clicks=Count('id', filter=F('interaction_type') == 'click'),
        conversions=Count('id', filter=F('interaction_type') == 'conversion'),
    )
    
    # Weekly metrics
    weekly_interactions = OfferInteraction.objects.filter(
        timestamp__date__gte=week_start
    ).aggregate(
        impressions=Count('id'),
        clicks=Count('id', filter=F('interaction_type') == 'click'),
    )
    
    # Monthly metrics
    monthly_interactions = OfferInteraction.objects.filter(
        timestamp__date__gte=month_start
    ).aggregate(
        impressions=Count('id'),
        clicks=Count('id', filter=F('interaction_type') == 'click'),
    )
    
    # Active offers
    active_offers = PartnerOffer.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).count()
    
    # Active partners
    active_partners = Partner.objects.filter(
        is_active=True
    ).count()
    
    analytics = {
        'daily': {
            'date': yesterday.isoformat(),
            'impressions': daily_interactions.get('impressions', 0) or 0,
            'clicks': daily_interactions.get('clicks', 0) or 0,
            'conversions': daily_interactions.get('conversions', 0) or 0,
        },
        'weekly': {
            'impressions': weekly_interactions.get('impressions', 0) or 0,
            'clicks': weekly_interactions.get('clicks', 0) or 0,
        },
        'monthly': {
            'impressions': monthly_interactions.get('impressions', 0) or 0,
            'clicks': monthly_interactions.get('clicks', 0) or 0,
        },
        'active_offers': active_offers,
        'active_partners': active_partners,
        'aggregated_at': timezone.now().isoformat()
    }
    
    # Cache for dashboards
    cache.set('advertising:analytics', analytics, timeout=86400)
    
    logger.info(f"Advertising analytics aggregated: {analytics['daily']}")
    return analytics


@shared_task
def process_new_advertiser_lead(lead_id: str):
    """
    Process new advertiser lead submission.
    
    Sends notifications and creates follow-up tasks.
    
    Usage:
        from advertising.tasks import process_new_advertiser_lead
        process_new_advertiser_lead.delay(str(lead.id))
    """
    from advertising.models import AdvertiserLead
    from accounts.models import User
    
    logger.info(f"Processing advertiser lead {lead_id}")
    
    try:
        lead = AdvertiserLead.objects.get(pk=lead_id)
        
        # Send confirmation to advertiser
        if lead.email:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject="YEA Poultry - Advertising Inquiry Received",
                message=f"""
Dear {lead.contact_name},

Thank you for your interest in advertising on YEA Poultry Platform!

We have received your inquiry and our team will contact you within 2-3 business days.

Your Details:
- Company: {lead.company_name}
- Budget Range: {lead.budget_range}
- Target Audience: {lead.target_audience or 'Not specified'}

Best regards,
YEA Poultry Advertising Team
                """,
                recipient_list=[lead.email]
            )
        
        # Notify admin team about new lead
        admin_emails = list(User.objects.filter(
            role__in=['SUPER_ADMIN', 'YEA_OFFICIAL'],
            is_active=True,
            email__isnull=False
        ).exclude(email='').values_list('email', flat=True)[:3])
        
        if admin_emails:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject=f"New Advertiser Lead: {lead.company_name}",
                message=f"""
New advertiser lead received:

Company: {lead.company_name}
Contact: {lead.contact_name}
Email: {lead.email}
Phone: {lead.phone_number or 'Not provided'}
Budget: {lead.budget_range}
Target: {lead.target_audience or 'Not specified'}
Notes: {lead.additional_notes or 'None'}

Please follow up within 2-3 business days.
                """,
                recipient_list=admin_emails
            )
        
        # Update lead status
        lead.status = 'contacted'
        lead.save(update_fields=['status'])
        
        logger.info(f"Advertiser lead {lead_id} processed successfully")
        return {'status': 'success', 'lead_id': lead_id}
    except AdvertiserLead.DoesNotExist:
        logger.error(f"Lead not found: {lead_id}")
        return {'status': 'error', 'error': 'Lead not found'}


@shared_task
def check_expiring_offers():
    """
    Check for offers expiring soon and notify partners.
    
    Sends notifications at 7 days and 1 day before expiry.
    """
    from advertising.models import PartnerOffer
    
    logger.info("Checking for expiring offers...")
    
    today = timezone.now().date()
    notifications_sent = 0
    
    for days_before in [7, 1]:
        expiry_date = today + timedelta(days=days_before)
        
        expiring_offers = PartnerOffer.objects.filter(
            is_active=True,
            end_date=expiry_date
        ).select_related('partner')
        
        for offer in expiring_offers:
            if offer.partner.contact_email:
                from core.tasks import send_email_async
                send_email_async.delay(
                    subject=f"Offer Expiring in {days_before} Day(s) - YEA Poultry",
                    message=f"""
Dear {offer.partner.company_name},

Your advertising offer "{offer.title}" will expire on {expiry_date.strftime('%B %d, %Y')}.

To continue your campaign, please contact our advertising team to renew your offer.

Current Performance:
- Impressions: {offer.analytics.get('impressions', 'N/A') if hasattr(offer, 'analytics') else 'Check dashboard'}
- Clicks: {offer.analytics.get('clicks', 'N/A') if hasattr(offer, 'analytics') else 'Check dashboard'}

Best regards,
YEA Poultry Advertising Team
                    """,
                    recipient_list=[offer.partner.contact_email]
                )
                notifications_sent += 1
    
    logger.info(f"Sent {notifications_sent} expiry notifications")
    return {'notifications_sent': notifications_sent}


@shared_task
def deactivate_expired_offers():
    """
    Deactivate offers that have passed their end date.
    
    Runs daily to clean up expired campaigns.
    """
    from advertising.models import PartnerOffer
    
    logger.info("Deactivating expired offers...")
    
    today = timezone.now().date()
    
    expired_offers = PartnerOffer.objects.filter(
        is_active=True,
        end_date__lt=today
    )
    
    count = expired_offers.count()
    expired_offers.update(is_active=False)
    
    logger.info(f"Deactivated {count} expired offers")
    return {'deactivated': count}


@shared_task
def calculate_partner_earnings():
    """
    Calculate partner earnings based on interaction metrics.
    
    For CPC/CPM pricing models.
    """
    from advertising.models import Partner, PartnerOffer, OfferInteraction, PartnerPayment
    from django.db.models import Sum
    
    logger.info("Calculating partner earnings...")
    
    today = timezone.now().date()
    month_start = today.replace(day=1)
    
    partners = Partner.objects.filter(is_active=True)
    
    earnings_calculated = 0
    for partner in partners:
        # Get all active offers for this partner
        offers = PartnerOffer.objects.filter(
            partner=partner,
            is_active=True
        )
        
        total_earnings = 0
        for offer in offers:
            # Count interactions this month
            interactions = OfferInteraction.objects.filter(
                offer=offer,
                timestamp__date__gte=month_start
            ).aggregate(
                clicks=Count('id', filter=F('interaction_type') == 'click'),
                conversions=Count('id', filter=F('interaction_type') == 'conversion')
            )
            
            # Calculate based on pricing model (simplified)
            # In production, this would use actual pricing from offer
            clicks = interactions.get('clicks', 0) or 0
            conversions = interactions.get('conversions', 0) or 0
            
            # Example: GHS 0.10 per click, GHS 5.00 per conversion
            offer_earnings = (clicks * 0.10) + (conversions * 5.00)
            total_earnings += offer_earnings
        
        if total_earnings > 0:
            # Update or create pending payment record
            # (Simplified - actual implementation would be more complex)
            logger.info(f"Partner {partner.id} earnings this month: GHS {total_earnings:.2f}")
            earnings_calculated += 1
    
    logger.info(f"Earnings calculated for {earnings_calculated} partners")
    return {'partners_calculated': earnings_calculated}


@shared_task
def generate_partner_report(partner_id: str, period: str = 'monthly'):
    """
    Generate performance report for a specific partner.
    
    Args:
        partner_id: UUID of the partner
        period: 'weekly' or 'monthly'
    """
    from advertising.models import Partner, PartnerOffer, OfferInteraction
    from django.core.cache import cache
    
    logger.info(f"Generating {period} report for partner {partner_id}")
    
    try:
        partner = Partner.objects.get(pk=partner_id)
        
        today = timezone.now().date()
        if period == 'weekly':
            start_date = today - timedelta(days=7)
        else:
            start_date = today.replace(day=1)
        
        # Get all offers for partner
        offers = PartnerOffer.objects.filter(partner=partner)
        
        offer_stats = []
        for offer in offers:
            interactions = OfferInteraction.objects.filter(
                offer=offer,
                timestamp__date__gte=start_date
            ).aggregate(
                impressions=Count('id'),
                clicks=Count('id', filter=F('interaction_type') == 'click'),
                conversions=Count('id', filter=F('interaction_type') == 'conversion')
            )
            
            offer_stats.append({
                'offer_id': str(offer.id),
                'offer_title': offer.title,
                'impressions': interactions.get('impressions', 0) or 0,
                'clicks': interactions.get('clicks', 0) or 0,
                'conversions': interactions.get('conversions', 0) or 0,
            })
        
        report = {
            'partner_id': str(partner.id),
            'company_name': partner.company_name,
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': today.isoformat(),
            'offers': offer_stats,
            'total_impressions': sum(o['impressions'] for o in offer_stats),
            'total_clicks': sum(o['clicks'] for o in offer_stats),
            'total_conversions': sum(o['conversions'] for o in offer_stats),
            'generated_at': timezone.now().isoformat()
        }
        
        # Cache the report
        cache_key = f'report:partner:{partner_id}:{period}'
        cache.set(cache_key, report, timeout=86400)
        
        # Send to partner email
        if partner.contact_email:
            from core.tasks import send_email_async
            send_email_async.delay(
                subject=f"Your {period.capitalize()} Advertising Report - YEA Poultry",
                message=f"""
{period.capitalize()} Advertising Performance Report
===================================

Company: {partner.company_name}
Period: {start_date.strftime('%B %d')} - {today.strftime('%B %d, %Y')}

Summary:
- Total Impressions: {report['total_impressions']:,}
- Total Clicks: {report['total_clicks']:,}
- Total Conversions: {report['total_conversions']:,}

View detailed analytics in your partner dashboard.

Best regards,
YEA Poultry Advertising Team
                """,
                recipient_list=[partner.contact_email]
            )
        
        logger.info(f"Partner report generated: {cache_key}")
        return {'status': 'success', 'cache_key': cache_key}
    except Partner.DoesNotExist:
        logger.error(f"Partner not found: {partner_id}")
        return {'status': 'error', 'error': 'Partner not found'}


@shared_task
def sync_conversion_data():
    """
    Sync conversion data from webhook logs.
    
    Processes pending conversion events and updates analytics.
    """
    from advertising.models import ConversionEvent, OfferInteraction
    
    logger.info("Syncing conversion data...")
    
    # Find unprocessed conversion events
    pending_events = ConversionEvent.objects.filter(
        processed=False
    ).order_by('created_at')[:100]  # Process in batches
    
    processed = 0
    for event in pending_events:
        try:
            # Create corresponding interaction record
            OfferInteraction.objects.create(
                offer_id=event.offer_id,
                interaction_type='conversion',
                farmer_id=event.farmer_id,
                metadata={
                    'conversion_event_id': str(event.id),
                    'conversion_type': event.conversion_type,
                    'value': float(event.value) if event.value else None
                }
            )
            
            event.processed = True
            event.save(update_fields=['processed'])
            processed += 1
        except Exception as exc:
            logger.error(f"Failed to process conversion event {event.id}: {exc}")
    
    logger.info(f"Synced {processed} conversion events")
    return {'processed': processed}
