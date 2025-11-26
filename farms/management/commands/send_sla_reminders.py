"""
Send SLA Reminders Management Command

Email officers about approaching SLA deadlines.
Schedule this to run daily (e.g., via cron at 8:00 AM):

    0 8 * * * cd /path/to/pms-backend && python manage.py send_sla_reminders
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from farms.models import FarmApprovalQueue
from collections import defaultdict


class Command(BaseCommand):
    help = 'Send reminder emails to officers about approaching SLA deadlines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Send reminders for items due within X days (default: 2)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending',
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        dry_run = options['dry_run']
        
        self.stdout.write(f'\n[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                         f'Sending SLA reminders (due within {days_threshold} days)...\n')
        
        # Get items due soon
        threshold_date = timezone.now() + timedelta(days=days_threshold)
        upcoming = FarmApprovalQueue.objects.filter(
            status__in=['pending', 'claimed'],
            sla_deadline__lte=threshold_date,
            sla_deadline__gte=timezone.now()
        ).select_related('farm', 'assigned_to')
        
        if not upcoming.exists():
            self.stdout.write(self.style.SUCCESS('✓ No upcoming deadlines found'))
            return
        
        # Group by officer
        officer_items = defaultdict(list)
        for item in upcoming:
            if item.assigned_to:
                officer_items[item.assigned_to].append(item)
        
        # Send reminders
        sent_count = 0
        for officer, items in officer_items.items():
            if not officer.email:
                self.stdout.write(
                    self.style.WARNING(f'⚠ {officer.get_full_name()} has no email - skipped')
                )
                continue
            
            # Prepare email
            subject = f'SLA Reminder: {len(items)} farm review(s) due soon'
            
            items_text = '\n'.join([
                f"  • {item.farm.farm_name} ({item.farm.application_id}) - "
                f"Due: {item.sla_deadline.strftime('%b %d, %Y')} - "
                f"Level: {item.review_level.title()}"
                for item in items
            ])
            
            days_until = (min(item.sla_deadline for item in items) - timezone.now()).days
            
            message = f"""
Dear {officer.get_full_name()},

This is a reminder about farm reviews assigned to you that are due within the next {days_threshold} days.

Pending Reviews ({len(items)}):
{items_text}

⏰ The earliest deadline is in {days_until} day(s).

Please log in to the system to complete these reviews:
{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'https://pms.yea.gov.gh'}/admin/farms/farmapprovalqueue/

Timely reviews help farmers get approved faster and maintain program efficiency.

Thank you,
YEA Poultry Management System
            """.strip()
            
            if dry_run:
                self.stdout.write(f'\n--- DRY RUN: Would send to {officer.email} ---')
                self.stdout.write(f'Subject: {subject}')
                self.stdout.write(message)
                self.stdout.write('---\n')
                sent_count += 1
            else:
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@yea-pms.gov.gh'),
                        recipient_list=[officer.email],
                        fail_silently=False,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Sent to {officer.get_full_name()} ({officer.email}): {len(items)} item(s)')
                    )
                    sent_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Failed to send to {officer.email}: {str(e)}')
                    )
        
        # Summary
        self.stdout.write(f'\n{"[DRY RUN] " if dry_run else ""}Summary:')
        self.stdout.write(f'  Total upcoming reviews: {upcoming.count()}')
        self.stdout.write(f'  Officers notified: {sent_count}')
        
        self.stdout.write(f'\n[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                         f'SLA reminders completed\n')
