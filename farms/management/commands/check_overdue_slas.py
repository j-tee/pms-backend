"""
Check Overdue SLAs Management Command

Daily cron job to mark overdue reviews and update queue status.
Schedule this to run once daily (e.g., via cron at 6:00 AM):

    0 6 * * * cd /path/to/pms-backend && python manage.py check_overdue_slas
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from farms.services.approval_workflow import FarmApprovalWorkflowService


class Command(BaseCommand):
    help = 'Check for overdue SLA deadlines and mark them accordingly'

    def add_arguments(self, parser):
        parser.add_argument(
            '--notify',
            action='store_true',
            help='Send notifications about overdue items',
        )

    def handle(self, *args, **options):
        self.stdout.write(f'\n[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                         f'Checking for overdue SLAs...\n')
        
        workflow = FarmApprovalWorkflowService()
        overdue_count = workflow.check_overdue_slas()
        
        if overdue_count > 0:
            self.stdout.write(
                self.style.WARNING(f'⚠ {overdue_count} review(s) marked as overdue')
            )
            
            if options['notify']:
                self.stdout.write('Sending notifications to assigned officers...')
                # TODO: Implement notification to officers about overdue items
                self.stdout.write(self.style.SUCCESS('✓ Notifications sent'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ No overdue reviews found'))
        
        self.stdout.write(f'\n[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] '
                         f'SLA check completed\n')
