"""
Management command to sync permissions to database.

Usage:
    python manage.py sync_permissions
"""

from django.core.management.base import BaseCommand
from accounts.services.permission_management_service import sync_permissions_to_database


class Command(BaseCommand):
    help = 'Sync all permissions from permissions_config.py to the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('Syncing permissions to database...'))
        
        result = sync_permissions_to_database()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Successfully synced {result["synced"]} permissions'
            )
        )
        
        if result['created'] > 0:
            self.stdout.write(
                self.style.SUCCESS(f'   - Created: {result["created"]} new permissions')
            )
        
        if result['updated'] > 0:
            self.stdout.write(
                self.style.SUCCESS(f'   - Updated: {result["updated"]} permissions')
            )
        
        if result['total'] > 0:
            self.stdout.write(
                self.style.MIGRATE_LABEL(f'   - Total in database: {result["total"]} permissions')
            )
