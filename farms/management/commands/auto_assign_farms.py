"""
Auto-Assign Farms Management Command

Auto-assign pending farms to officers based on GPS location suggestions.
Can be run manually or scheduled via cron:

    0 */6 * * * cd /path/to/pms-backend && python manage.py auto_assign_farms
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from farms.models import FarmApprovalQueue
from accounts.models import User


class Command(BaseCommand):
    help = 'Auto-assign pending farms based on GPS location suggestions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--level',
            type=str,
            choices=['constituency', 'regional', 'national'],
            help='Only auto-assign at specific level',
        )
        parser.add_argument(
            '--max-per-officer',
            type=int,
            default=10,
            help='Maximum farms to assign per officer (default: 10)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be assigned without actually assigning',
        )

    def handle(self, *args, **options):
        level = options.get('level')
        max_per_officer = options['max_per_officer']
        dry_run = options['dry_run']
        
        self.stdout.write(f'\n[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                         f'Auto-assigning pending farms...\n')
        
        # Get pending items with suggestions
        query = Q(status='pending', assigned_to__isnull=True)
        if level:
            query &= Q(review_level=level)
        
        pending = FarmApprovalQueue.objects.filter(query).select_related('farm')
        
        if not pending.exists():
            self.stdout.write(self.style.SUCCESS('✓ No pending farms to auto-assign'))
            return
        
        self.stdout.write(f'Found {pending.count()} pending farm(s) for auto-assignment')
        
        # Process by level
        assigned_count = 0
        
        for item in pending:
            # Get suggestion based on level
            if item.review_level == 'constituency':
                suggested_area = item.suggested_constituency
                officer_filter = Q(role='constituency_officer')
                # TODO: Add constituency field to User model for better matching
            elif item.review_level == 'regional':
                suggested_area = item.suggested_region
                officer_filter = Q(role='regional_officer')
                # TODO: Add region field to User model for better matching
            else:  # national
                suggested_area = 'National'
                officer_filter = Q(role='national_admin')
            
            if not suggested_area:
                self.stdout.write(
                    self.style.WARNING(f'⚠ {item.farm.farm_name}: No GPS suggestion available - skipped')
                )
                continue
            
            # Find officers with capacity
            officers = User.objects.filter(officer_filter, is_active=True)
            
            # Count current assignments for each officer
            officer_loads = {}
            for officer in officers:
                current_load = FarmApprovalQueue.objects.filter(
                    assigned_to=officer,
                    status__in=['pending', 'claimed']
                ).count()
                if current_load < max_per_officer:
                    officer_loads[officer] = current_load
            
            if not officer_loads:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ {item.farm.farm_name}: No officers with capacity at '
                        f'{item.review_level} level - skipped'
                    )
                )
                continue
            
            # Assign to officer with least load
            assigned_officer = min(officer_loads, key=officer_loads.get)
            
            if dry_run:
                self.stdout.write(
                    f'  [DRY RUN] Would assign: {item.farm.farm_name} → '
                    f'{assigned_officer.get_full_name()} '
                    f'(current load: {officer_loads[assigned_officer]})'
                )
                assigned_count += 1
            else:
                item.assigned_to = assigned_officer
                item.assigned_at = timezone.now()
                item.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Assigned: {item.farm.farm_name} → '
                        f'{assigned_officer.get_full_name()} '
                        f'({item.review_level} level, {suggested_area})'
                    )
                )
                assigned_count += 1
        
        # Summary
        self.stdout.write(f'\n{"[DRY RUN] " if dry_run else ""}Summary:')
        self.stdout.write(f'  Total pending: {pending.count()}')
        self.stdout.write(f'  Auto-assigned: {assigned_count}')
        
        if not dry_run and assigned_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    '\n💡 Assigned officers will receive notifications about new assignments'
                )
            )
        
        self.stdout.write(f'\n[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                         f'Auto-assignment completed\n')
