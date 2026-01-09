"""
Management command to recalculate customer stats (total_orders, total_purchases)
from completed marketplace orders, egg sales, and bird sales.

Run with: python manage.py recalculate_customer_stats
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
from decimal import Decimal

from sales_revenue.models import Customer, EggSale, BirdSale
from sales_revenue.marketplace_models import MarketplaceOrder


class Command(BaseCommand):
    help = 'Recalculate customer stats (total_orders, total_purchases) from all sales sources'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        customers = Customer.objects.all()
        updated_count = 0
        
        for customer in customers:
            # Get completed marketplace orders
            marketplace_stats = MarketplaceOrder.objects.filter(
                customer=customer,
                status='completed'
            ).aggregate(
                count=Count('id'),
                total=Sum('total_amount')
            )
            
            # Get egg sales
            egg_stats = EggSale.objects.filter(customer=customer).aggregate(
                count=Count('id'),
                total=Sum('subtotal')
            )
            
            # Get bird sales
            bird_stats = BirdSale.objects.filter(customer=customer).aggregate(
                count=Count('id'),
                total=Sum('subtotal')
            )
            
            # Calculate combined stats
            new_total_orders = (
                (marketplace_stats['count'] or 0) +
                (egg_stats['count'] or 0) +
                (bird_stats['count'] or 0)
            )
            new_total_purchases = (
                (marketplace_stats['total'] or Decimal('0')) +
                (egg_stats['total'] or Decimal('0')) +
                (bird_stats['total'] or Decimal('0'))
            )
            
            # Check if update is needed
            if (customer.total_orders != new_total_orders or 
                customer.total_purchases != new_total_purchases):
                
                self.stdout.write(
                    f"Customer: {customer.get_full_name()} (ID: {customer.id})\n"
                    f"  Orders: {customer.total_orders} -> {new_total_orders}\n"
                    f"  Purchases: {customer.total_purchases} -> {new_total_purchases}"
                )
                
                if not dry_run:
                    customer.total_orders = new_total_orders
                    customer.total_purchases = new_total_purchases
                    customer.save(update_fields=['total_orders', 'total_purchases'])
                
                updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nWould update {updated_count} customers')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nUpdated {updated_count} customers')
            )
