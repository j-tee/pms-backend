"""
Initialize Platform Settings

Creates default platform settings if they don't exist.
Run this after initial migration.

Usage:
    python manage.py init_platform_settings
"""

from django.core.management.base import BaseCommand
from sales_revenue.models import PlatformSettings


class Command(BaseCommand):
    help = 'Initialize platform settings with default values'

    def handle(self, *args, **options):
        # Check if settings already exist
        if PlatformSettings.objects.exists():
            settings = PlatformSettings.objects.first()
            self.stdout.write(
                self.style.WARNING(
                    f'Platform settings already exist (last updated: {settings.updated_at})'
                )
            )
            self.stdout.write('Use Django admin to modify settings.')
            return
        
        # Create default settings
        settings = PlatformSettings.objects.create(
            commission_tier_1_percentage=5.0,
            commission_tier_1_threshold=100.0,
            commission_tier_2_percentage=3.0,
            commission_tier_2_threshold=500.0,
            commission_tier_3_percentage=2.0,
            commission_minimum_amount=2.0,
            paystack_fee_bearer='account',
            paystack_settlement_schedule='auto',
            payment_retry_max_attempts=3,
            payment_retry_delay_seconds=300,
            refund_eligibility_hours=48,
            payment_auto_refund_hours=72,
            enable_instant_settlements=False,
            enable_refunds=True,
            enable_auto_refunds=True,
            notes='Initial platform settings created automatically'
        )
        
        self.stdout.write(
            self.style.SUCCESS('✅ Platform settings initialized successfully!')
        )
        self.stdout.write('')
        self.stdout.write('Commission Structure:')
        self.stdout.write(f'  • Tier 1: {settings.commission_tier_1_percentage}% (< GHS {settings.commission_tier_1_threshold})')
        self.stdout.write(f'  • Tier 2: {settings.commission_tier_2_percentage}% (GHS {settings.commission_tier_1_threshold}-{settings.commission_tier_2_threshold})')
        self.stdout.write(f'  • Tier 3: {settings.commission_tier_3_percentage}% (> GHS {settings.commission_tier_2_threshold})')
        self.stdout.write(f'  • Minimum: GHS {settings.commission_minimum_amount}')
        self.stdout.write('')
        self.stdout.write('Payment Configuration:')
        self.stdout.write(f'  • Fee bearer: {settings.get_paystack_fee_bearer_display()}')
        self.stdout.write(f'  • Settlement: {settings.get_paystack_settlement_schedule_display()}')
        self.stdout.write(f'  • Retry attempts: {settings.payment_retry_max_attempts}')
        self.stdout.write(f'  • Retry delay: {settings.payment_retry_delay_seconds} seconds')
        self.stdout.write('')
        self.stdout.write('Refund Policy:')
        self.stdout.write(f'  • Request window: {settings.refund_eligibility_hours} hours')
        self.stdout.write(f'  • Auto-refund after: {settings.payment_auto_refund_hours} hours')
        self.stdout.write(f'  • Refunds enabled: {settings.enable_refunds}')
        self.stdout.write(f'  • Auto-refunds enabled: {settings.enable_auto_refunds}')
        self.stdout.write('')
        self.stdout.write('To modify settings, go to: Django Admin > Sales Revenue > Platform Settings')
