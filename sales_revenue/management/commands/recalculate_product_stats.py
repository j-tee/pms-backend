"""
Management command to recalculate product stats (total_sold, total_revenue)
from completed marketplace orders.

Run with: python manage.py recalculate_product_stats
"""

from django.core.management.base import BaseCommand
from django.db.models import Sum, Count
from decimal import Decimal

from sales_revenue.marketplace_models import Product, OrderItem


class Command(BaseCommand):
    help = 'Recalculate product stats (total_sold, total_revenue) from completed orders'

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
        
        products = Product.objects.all()
        updated_count = 0
        
        for product in products:
            # Get completed order items for this product
            stats = OrderItem.objects.filter(
                product=product,
                order__status='completed'
            ).aggregate(
                total_sold=Sum('quantity'),
                total_revenue=Sum('line_total')
            )
            
            new_total_sold = stats['total_sold'] or 0
            new_total_revenue = stats['total_revenue'] or Decimal('0')
            
            # Check if update is needed
            if (product.total_sold != new_total_sold or 
                product.total_revenue != new_total_revenue):
                
                self.stdout.write(
                    f"Product: {product.name} (ID: {product.id})\n"
                    f"  Sold: {product.total_sold} -> {new_total_sold}\n"
                    f"  Revenue: {product.total_revenue} -> {new_total_revenue}"
                )
                
                if not dry_run:
                    product.total_sold = new_total_sold
                    product.total_revenue = new_total_revenue
                    product.save(update_fields=['total_sold', 'total_revenue'])
                
                updated_count += 1
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'\nWould update {updated_count} products')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nUpdated {updated_count} products')
            )
