"""
Backfill Primary Farm Locations

Creates a primary FarmLocation for approved farms that don't have any locations yet.
Uses data from the farm's associated application where available.
"""

from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from farms.models import Farm, FarmLocation
from farms.application_models import FarmApplication


class Command(BaseCommand):
    help = 'Create primary locations for farms that have no locations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--farm-id',
            type=str,
            help='Backfill location for a specific farm ID',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        farm_id = options.get('farm_id')

        self.stdout.write(self.style.WARNING(
            '=' * 70
        ))
        self.stdout.write(self.style.WARNING(
            'Backfill Primary Farm Locations'
        ))
        self.stdout.write(self.style.WARNING(
            '=' * 70
        ))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Get farms without locations
        if farm_id:
            farms_qs = Farm.objects.filter(id=farm_id)
        else:
            farms_qs = Farm.objects.filter(application_status='Approved')
        
        farms_without_locations = []
        for farm in farms_qs:
            location_count = FarmLocation.objects.filter(farm=farm).count()
            if location_count == 0:
                farms_without_locations.append(farm)
        
        if not farms_without_locations:
            self.stdout.write(self.style.SUCCESS(
                '✓ All approved farms already have locations!'
            ))
            return
        
        self.stdout.write(self.style.NOTICE(
            f'\nFound {len(farms_without_locations)} farm(s) without locations:\n'
        ))
        
        created_count = 0
        error_count = 0
        
        for farm in farms_without_locations:
            self.stdout.write(f'  • {farm.farm_name} (ID: {farm.id})')
            self.stdout.write(f'    User: {farm.user.email}')
            self.stdout.write(f'    Constituency: {farm.primary_constituency}')
            
            # Try to get application data
            try:
                application = FarmApplication.objects.get(farm_profile=farm)
                location_description = getattr(application, 'farm_location_description', '')
                land_size = getattr(application, 'land_size_acres', 0)
            except FarmApplication.DoesNotExist:
                location_description = f'Primary location for {farm.farm_name}'
                land_size = 0
                self.stdout.write(self.style.WARNING(
                    f'    ⚠️  No application found - using defaults'
                ))
            
            if not dry_run:
                try:
                    # Placeholder coordinates (center of Ghana)
                    # Farmer should update with actual Ghana Post GPS address
                    placeholder_lat = 7.9465
                    placeholder_lon = -1.0232
                    
                    location = FarmLocation.objects.create(
                        farm=farm,
                        gps_address_string='PENDING-GPS-UPDATE',
                        location=Point(placeholder_lon, placeholder_lat),
                        region=getattr(farm, 'region', '') if hasattr(farm, 'region') else '',
                        district=getattr(farm, 'district', '') if hasattr(farm, 'district') else '',
                        constituency=farm.primary_constituency,
                        community='',
                        land_size_acres=land_size,
                        land_ownership_status='Owned',
                        is_primary_location=True,
                        road_accessibility='All Year',
                        nearest_landmark=location_description[:200] if location_description else '',
                    )
                    
                    self.stdout.write(self.style.SUCCESS(
                        f'    ✓ Created primary location (ID: {location.id})'
                    ))
                    created_count += 1
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f'    ✗ Error creating location: {e}'
                    ))
                    error_count += 1
            else:
                self.stdout.write(self.style.NOTICE(
                    f'    → Would create primary location with placeholder GPS'
                ))
            
            self.stdout.write('')  # Blank line
        
        # Summary
        self.stdout.write(self.style.WARNING('=' * 70))
        if dry_run:
            self.stdout.write(self.style.NOTICE(
                f'Would create {len(farms_without_locations)} primary location(s)'
            ))
            self.stdout.write(self.style.NOTICE(
                '\nRun without --dry-run to apply changes'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created {created_count} primary location(s)'
            ))
            if error_count > 0:
                self.stdout.write(self.style.ERROR(
                    f'✗ {error_count} error(s) occurred'
                ))
        self.stdout.write(self.style.WARNING('=' * 70))
