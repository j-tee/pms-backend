"""
Management command to backfill location data for FARMER users.
This syncs region, district, and constituency from Farm/FarmLocation/FarmApplication.
"""
from django.core.management.base import BaseCommand
from accounts.models import User
from farms.models import Farm
from farms.application_models import FarmApplication


class Command(BaseCommand):
    help = 'Backfill location data (region, district, constituency) for FARMER users from their farm registration data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Only update a specific user by username',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        username = options.get('username')

        # Get all farmers
        farmers = User.objects.filter(role='FARMER')
        
        if username:
            farmers = farmers.filter(username=username)
            
        total_farmers = farmers.count()
        updated_count = 0
        skipped_count = 0
        no_source_count = 0

        self.stdout.write(f"Processing {total_farmers} FARMER users...")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))

        for user in farmers:
            location_data = self._get_location_for_user(user)
            
            if not location_data:
                no_source_count += 1
                self.stdout.write(f"  {user.username}: No farm/application data found")
                continue
            
            # Check if update is needed
            needs_update = (
                user.region != location_data.get('region', '') or
                user.district != location_data.get('district', '') or
                user.constituency != location_data.get('constituency')
            )
            
            if not needs_update:
                skipped_count += 1
                if options['verbosity'] >= 2:
                    self.stdout.write(f"  {user.username}: Already up to date")
                continue
            
            # Show what we're updating
            self.stdout.write(
                f"  {user.username}: "
                f"region='{location_data.get('region', '')}', "
                f"district='{location_data.get('district', '')}', "
                f"constituency='{location_data.get('constituency', '')}' "
                f"(source: {location_data['source']})"
            )
            
            if not dry_run:
                user.region = location_data.get('region', '') or ''
                user.district = location_data.get('district', '') or ''
                user.constituency = location_data.get('constituency')
                user.save(update_fields=['region', 'district', 'constituency'])
                
            updated_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Summary:"))
        self.stdout.write(f"  Total farmers: {total_farmers}")
        self.stdout.write(f"  Updated: {updated_count}")
        self.stdout.write(f"  Skipped (already correct): {skipped_count}")
        self.stdout.write(f"  No source data: {no_source_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nThis was a dry run. Run without --dry-run to apply changes."))

    def _get_location_for_user(self, user):
        """
        Get location data from Farm, FarmLocation, or FarmApplication.
        Priority: FarmLocation > Farm.primary_constituency > FarmApplication
        """
        # Try to get from Farm's primary location
        try:
            farm = Farm.objects.filter(user=user).first()
            if farm:
                # Try FarmLocation first
                primary_location = farm.locations.filter(is_primary_location=True).first()
                if not primary_location:
                    primary_location = farm.locations.first()
                
                if primary_location:
                    return {
                        'region': primary_location.region,
                        'district': primary_location.district,
                        'constituency': primary_location.constituency,
                        'source': 'farm_location'
                    }
                
                # Fallback to farm.primary_constituency
                if farm.primary_constituency:
                    return {
                        'region': '',
                        'district': '',
                        'constituency': farm.primary_constituency,
                        'source': 'farm_constituency'
                    }
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Error reading farm: {e}"))
        
        # Try FarmApplication
        try:
            application = FarmApplication.objects.filter(user_account=user).first()
            if application:
                return {
                    'region': application.region or '',
                    'district': application.district or '',
                    'constituency': application.primary_constituency,
                    'source': 'farm_application'
                }
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Error reading application: {e}"))
        
        return None
