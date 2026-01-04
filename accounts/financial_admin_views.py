"""
Financial Admin Views

Provides endpoints for financial reporting, payment history, revenue analytics,
and subscriber management for YEA officials and super admins.

Endpoints:
    GET /api/admin/payments/ - Payment history with filters
    GET /api/admin/revenue/summary/ - Revenue breakdown and trends
    GET /api/admin/subscribers/ - Active marketplace subscribers
    GET /api/admin/finance/dashboard/ - Financial dashboard stats
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import models
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from farms.models import Farm
from subscriptions.models import Subscription, SubscriptionPayment

logger = logging.getLogger(__name__)


class IsFinanceAdmin(IsAuthenticated):
    """
    Permission class for financial admin endpoints.
    Allows: SUPER_ADMIN, YEA_OFFICIAL, NATIONAL_ADMIN
    """
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        allowed_roles = ['SUPER_ADMIN', 'YEA_OFFICIAL', 'NATIONAL_ADMIN']
        return request.user.role in allowed_roles


class PaymentHistoryView(APIView):
    """
    GET /api/admin/payments/
    
    List all payments with filtering and search capabilities.
    
    Query Parameters:
        - status: completed, pending, failed, refunded
        - payment_type: marketplace_activation, subscription_renewal, verified_seller
        - payment_method: momo, bank, card, cash
        - date_from: YYYY-MM-DD
        - date_to: YYYY-MM-DD
        - search: Search by farm name, farmer name, reference
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20)
    """
    permission_classes = [IsFinanceAdmin]
    
    def get(self, request):
        # Build query
        payments = SubscriptionPayment.objects.select_related(
            'subscription__farm__user',
            'subscription__plan',
            'verified_by'
        ).order_by('-payment_date', '-created_at')
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            payments = payments.filter(status=status_filter)
        
        payment_method = request.query_params.get('payment_method')
        if payment_method:
            # Map frontend values to model values
            method_map = {
                'momo': 'mobile_money',
                'bank': 'bank_transfer',
                'card': 'card',
                'cash': 'cash',
            }
            payments = payments.filter(payment_method=method_map.get(payment_method, payment_method))
        
        # Date range filters
        date_from = request.query_params.get('date_from')
        if date_from:
            try:
                start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                payments = payments.filter(payment_date__gte=start_date)
            except ValueError:
                pass
        
        date_to = request.query_params.get('date_to')
        if date_to:
            try:
                end_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                payments = payments.filter(payment_date__lte=end_date)
            except ValueError:
                pass
        
        # Search
        search = request.query_params.get('search')
        if search:
            payments = payments.filter(
                Q(subscription__farm__farm_name__icontains=search) |
                Q(subscription__farm__user__first_name__icontains=search) |
                Q(subscription__farm__user__last_name__icontains=search) |
                Q(payment_reference__icontains=search) |
                Q(gateway_transaction_id__icontains=search)
            )
        
        # Calculate totals before pagination
        total_amount = payments.filter(status='completed').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        total_count = payments.count()
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        offset = (page - 1) * page_size
        
        paginated_payments = payments[offset:offset + page_size]
        
        # Format response
        results = []
        for payment in paginated_payments:
            farm = payment.subscription.farm if payment.subscription else None
            user = farm.user if farm else None
            
            # Determine payment type based on context
            payment_type = self._determine_payment_type(payment)
            
            results.append({
                'id': str(payment.id),
                'farm_id': str(farm.id) if farm else None,
                'farm_name': farm.farm_name if farm else 'N/A',
                'farmer_name': user.get_full_name() if user else 'N/A',
                'farmer_phone': str(farm.primary_phone) if farm else None,
                'amount': str(payment.amount),
                'payment_type': payment_type,
                'payment_method': self._format_payment_method(payment.payment_method),
                'transaction_reference': payment.payment_reference or payment.gateway_transaction_id,
                'status': payment.status,
                'paid_at': payment.created_at.isoformat() if payment.status == 'completed' else None,
                'period_start': payment.period_start.isoformat() if payment.period_start else None,
                'period_end': payment.period_end.isoformat() if payment.period_end else None,
                'verified_by': payment.verified_by.get_full_name() if payment.verified_by else None,
                'notes': payment.notes,
            })
        
        return Response({
            'results': results,
            'count': total_count,
            'total_amount': str(total_amount),
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
        })
    
    def _determine_payment_type(self, payment):
        """Determine payment type from payment context"""
        if payment.subscription and payment.subscription.farm:
            farm = payment.subscription.farm
            if farm.subscription_type == 'verified':
                return 'verified_seller'
            elif payment.subscription.status == 'trial':
                return 'marketplace_activation'
        return 'subscription_renewal'
    
    def _format_payment_method(self, method):
        """Format payment method for frontend"""
        method_map = {
            'mobile_money': 'momo',
            'bank_transfer': 'bank',
            'card': 'card',
            'cash': 'cash',
        }
        return method_map.get(method, method)


class RevenueSummaryView(APIView):
    """
    GET /api/admin/revenue/summary/
    
    Get revenue breakdown with period comparisons.
    
    Query Parameters:
        - period: daily, weekly, monthly, yearly (default: monthly)
        - year: Year to filter (default: current year)
        - month: Month to filter (for daily period)
    """
    permission_classes = [IsFinanceAdmin]
    
    def get(self, request):
        period = request.query_params.get('period', 'monthly')
        year = int(request.query_params.get('year', timezone.now().year))
        month = request.query_params.get('month')
        
        # Base query - completed payments only
        payments = SubscriptionPayment.objects.filter(
            status='completed'
        ).select_related('subscription__farm')
        
        # Apply year filter
        payments = payments.filter(payment_date__year=year)
        
        if month and period == 'daily':
            payments = payments.filter(payment_date__month=int(month))
        
        # Calculate total revenue
        total_revenue = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Get breakdown by period
        breakdown = self._get_period_breakdown(payments, period)
        
        # Get breakdown by type
        by_type = self._get_type_breakdown(payments)
        
        # Get comparison with previous period
        comparison = self._get_period_comparison(period, year, month)
        
        return Response({
            'total_revenue': str(total_revenue),
            'period': period,
            'year': year,
            'breakdown': breakdown,
            'by_type': by_type,
            'comparison': comparison,
        })
    
    def _get_period_breakdown(self, payments, period):
        """Get revenue breakdown by period"""
        if period == 'daily':
            trunc_func = TruncDay('payment_date')
            date_format = '%Y-%m-%d'
        elif period == 'weekly':
            trunc_func = TruncWeek('payment_date')
            date_format = '%Y-W%W'
        elif period == 'yearly':
            # For yearly, group by year
            breakdown = payments.values('payment_date__year').annotate(
                amount=Sum('amount'),
                transaction_count=Count('id')
            ).order_by('payment_date__year')
            
            return [{
                'year': str(item['payment_date__year']),
                'amount': str(item['amount'] or Decimal('0.00')),
                'transaction_count': item['transaction_count'],
            } for item in breakdown]
        else:  # monthly
            trunc_func = TruncMonth('payment_date')
            date_format = '%Y-%m'
        
        breakdown = payments.annotate(
            period_date=trunc_func
        ).values('period_date').annotate(
            amount=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('period_date')
        
        return [{
            'month' if period == 'monthly' else 'date': item['period_date'].strftime(date_format),
            'amount': str(item['amount'] or Decimal('0.00')),
            'transaction_count': item['transaction_count'],
        } for item in breakdown]
    
    def _get_type_breakdown(self, payments):
        """Get revenue breakdown by payment type"""
        # Since we don't have explicit payment_type field, derive from subscription
        marketplace_activation = Decimal('0.00')
        verified_seller_fees = Decimal('0.00')
        transaction_commission = Decimal('0.00')
        
        for payment in payments:
            if payment.subscription and payment.subscription.farm:
                farm = payment.subscription.farm
                if farm.subscription_type == 'verified':
                    verified_seller_fees += payment.amount
                else:
                    marketplace_activation += payment.amount
            else:
                marketplace_activation += payment.amount
        
        return {
            'marketplace_activation': str(marketplace_activation),
            'verified_seller_fees': str(verified_seller_fees),
            'transaction_commission': str(transaction_commission),
        }
    
    def _get_period_comparison(self, period, year, month=None):
        """Compare with previous period"""
        now = timezone.now()
        
        # Current period
        if period == 'monthly':
            current_start = now.replace(day=1)
            previous_start = (current_start - timedelta(days=1)).replace(day=1)
            previous_end = current_start - timedelta(days=1)
        elif period == 'yearly':
            current_start = now.replace(month=1, day=1)
            previous_start = current_start.replace(year=year - 1)
            previous_end = current_start - timedelta(days=1)
        else:
            # Default to monthly comparison
            current_start = now.replace(day=1)
            previous_start = (current_start - timedelta(days=1)).replace(day=1)
            previous_end = current_start - timedelta(days=1)
        
        previous_revenue = SubscriptionPayment.objects.filter(
            status='completed',
            payment_date__gte=previous_start.date(),
            payment_date__lte=previous_end.date()
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        current_revenue = SubscriptionPayment.objects.filter(
            status='completed',
            payment_date__gte=current_start.date()
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Calculate growth
        if previous_revenue > 0:
            growth = ((current_revenue - previous_revenue) / previous_revenue) * 100
        else:
            growth = Decimal('100.00') if current_revenue > 0 else Decimal('0.00')
        
        return {
            'previous_period': str(previous_revenue),
            'current_period': str(current_revenue),
            'growth_percentage': str(round(growth, 2)),
        }


class ActiveSubscribersView(APIView):
    """
    GET /api/admin/subscribers/
    
    List marketplace subscribers with status and tier information.
    
    Query Parameters:
        - status: active, trial, grace_period, expired
        - tier: standard, verified, government_subsidized
        - search: Search by farm name, farmer name
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20)
    """
    permission_classes = [IsFinanceAdmin]
    
    def get(self, request):
        # Build query from Farm model (subscription info is on Farm)
        farms = Farm.objects.filter(
            marketplace_enabled=True
        ).select_related('user', 'subscription').order_by('-created_at')
        
        # Status filter (mapped to farm/subscription state)
        status_filter = request.query_params.get('status')
        if status_filter:
            if status_filter == 'active':
                farms = farms.filter(
                    Q(subscription__status='active') | Q(government_subsidy_active=True)
                )
            elif status_filter == 'trial':
                farms = farms.filter(subscription__status='trial')
            elif status_filter == 'grace_period':
                farms = farms.filter(subscription__status='past_due')
            elif status_filter == 'expired':
                farms = farms.filter(
                    Q(subscription__status__in=['suspended', 'cancelled']) |
                    Q(marketplace_enabled=False)
                )
        
        # Tier filter
        tier = request.query_params.get('tier')
        if tier:
            farms = farms.filter(subscription_type=tier)
        
        # Search
        search = request.query_params.get('search')
        if search:
            farms = farms.filter(
                Q(farm_name__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(farm_id__icontains=search)
            )
        
        total_count = farms.count()
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        offset = (page - 1) * page_size
        
        paginated_farms = farms[offset:offset + page_size]
        
        # Format results
        results = []
        for farm in paginated_farms:
            subscription = getattr(farm, 'subscription', None)
            
            # Determine subscription status
            if farm.government_subsidy_active:
                sub_status = 'active'
                tier_name = 'government_subsidized'
            elif subscription:
                sub_status = subscription.status
                tier_name = farm.subscription_type
            else:
                sub_status = 'none'
                tier_name = 'none'
            
            # Calculate days remaining
            days_remaining = None
            expires_at = None
            if subscription and subscription.current_period_end:
                expires_at = subscription.current_period_end.isoformat()
                delta = subscription.current_period_end - timezone.now().date()
                days_remaining = max(0, delta.days)
            elif farm.government_subsidy_end_date:
                expires_at = farm.government_subsidy_end_date.isoformat()
                delta = farm.government_subsidy_end_date - timezone.now().date()
                days_remaining = max(0, delta.days)
            
            # Calculate total paid
            total_paid = Decimal('0.00')
            last_payment_date = None
            if subscription:
                payment_agg = subscription.payments.filter(status='completed').aggregate(
                    total=Sum('amount'),
                    last_date=models.Max('payment_date')
                )
                total_paid = payment_agg['total'] or Decimal('0.00')
                last_payment_date = payment_agg['last_date']
            
            results.append({
                'farm_id': str(farm.id),
                'farm_name': farm.farm_name,
                'farmer_name': farm.user.get_full_name() if farm.user else 'N/A',
                'tier': tier_name,
                'subscription_status': sub_status,
                'started_at': subscription.start_date.isoformat() if subscription and subscription.start_date else None,
                'expires_at': expires_at,
                'days_remaining': days_remaining,
                'total_paid': str(total_paid),
                'last_payment_date': last_payment_date.isoformat() if last_payment_date else None,
            })
        
        # Calculate summary statistics
        summary = self._get_summary_stats()
        
        return Response({
            'results': results,
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
            'summary': summary,
        })
    
    def _get_summary_stats(self):
        """Calculate summary statistics for subscribers"""
        # Active subscriptions
        active_subs = Subscription.objects.filter(status='active').count()
        trial_subs = Subscription.objects.filter(status='trial').count()
        grace_period = Subscription.objects.filter(status='past_due').count()
        expired = Subscription.objects.filter(status__in=['suspended', 'cancelled']).count()
        
        # By tier from Farm model
        standard = Farm.objects.filter(subscription_type='standard', marketplace_enabled=True).count()
        verified = Farm.objects.filter(subscription_type='verified', marketplace_enabled=True).count()
        government = Farm.objects.filter(government_subsidy_active=True).count()
        
        return {
            'total_active': active_subs + government,
            'total_trial': trial_subs,
            'total_grace_period': grace_period,
            'total_expired': expired,
            'by_tier': {
                'standard': standard,
                'verified': verified,
                'government_subsidized': government,
            }
        }


class FinanceDashboardView(APIView):
    """
    GET /api/admin/finance/dashboard/
    
    Financial dashboard with key metrics for quick overview.
    """
    permission_classes = [IsFinanceAdmin]
    
    def get(self, request):
        now = timezone.now()
        today = now.date()
        
        # Calculate date ranges
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        
        # Today's stats
        today_stats = self._get_period_stats(today, today)
        
        # This week's stats
        week_stats = self._get_period_stats(week_start, today)
        
        # This month's stats
        month_stats = self._get_period_stats(month_start, today)
        
        # Pending payments
        pending_payments = SubscriptionPayment.objects.filter(status='pending')
        pending_count = pending_payments.count()
        pending_amount = pending_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Expiring soon
        expiring_7_days = Subscription.objects.filter(
            status__in=['active', 'trial'],
            current_period_end__lte=today + timedelta(days=7),
            current_period_end__gte=today
        ).count()
        
        expiring_30_days = Subscription.objects.filter(
            status__in=['active', 'trial'],
            current_period_end__lte=today + timedelta(days=30),
            current_period_end__gte=today
        ).count()
        
        # Recent payments (last 5 for quick view)
        recent_payments = SubscriptionPayment.objects.filter(
            status='completed'
        ).select_related('subscription__farm__user').order_by('-created_at')[:5]
        
        recent_payments_list = [{
            'id': str(p.id),
            'farm_name': p.subscription.farm.farm_name if p.subscription and p.subscription.farm else 'N/A',
            'amount': str(p.amount),
            'payment_method': p.payment_method,
            'paid_at': p.created_at.isoformat(),
        } for p in recent_payments]
        
        # Get AdSense data if available
        adsense_data = self._get_adsense_summary()
        
        return Response({
            'today': today_stats,
            'this_week': week_stats,
            'this_month': month_stats,
            'pending_payments': {
                'count': pending_count,
                'amount': str(pending_amount),
            },
            'expiring_soon': {
                'count': expiring_30_days,
                'in_7_days': expiring_7_days,
                'in_30_days': expiring_30_days,
            },
            'recent_payments': recent_payments_list,
            'adsense': adsense_data,
        })
    
    def _get_adsense_summary(self):
        """Get AdSense earnings summary if connected"""
        try:
            from core.adsense_service import get_adsense_service
            
            service = get_adsense_service()
            
            if not service.is_available():
                return {
                    'connected': False,
                    'message': 'AdSense not connected'
                }
            
            summary = service.get_earnings_summary()
            
            # Convert Decimals to strings
            for key in ['today', 'yesterday', 'this_week', 'this_month', 'last_month']:
                if key in summary and isinstance(summary[key], Decimal):
                    summary[key] = str(summary[key])
            
            return {
                'connected': True,
                'today': summary.get('today', '0.00'),
                'this_week': summary.get('this_week', '0.00'),
                'this_month': summary.get('this_month', '0.00'),
                'currency': summary.get('currency', 'USD'),
            }
            
        except Exception as e:
            logger.warning(f"Failed to get AdSense data: {e}")
            return {
                'connected': False,
                'error': str(e)
            }
    
    def _get_period_stats(self, start_date, end_date):
        """Get financial stats for a date range"""
        payments = SubscriptionPayment.objects.filter(
            status='completed',
            payment_date__gte=start_date,
            payment_date__lte=end_date
        )
        
        revenue = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        transaction_count = payments.count()
        
        # New subscribers in period
        new_subscribers = Subscription.objects.filter(
            start_date__gte=start_date,
            start_date__lte=end_date
        ).count()
        
        return {
            'revenue': str(revenue),
            'transactions': transaction_count,
            'new_subscribers': new_subscribers,
        }
