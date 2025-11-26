"""
Management command to run fraud detection on farms.

Usage:
    python manage.py detect_fraud                    # Scan all active farms
    python manage.py detect_fraud --farm-id 123      # Scan specific farm
    python manage.py detect_fraud --days 30          # Custom analysis period
    python manage.py detect_fraud --min-risk MEDIUM  # Only show MEDIUM+ alerts
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from farms.models import Farm
from sales_revenue.models import FraudAlert
from sales_revenue.services.fraud_detection_service import FraudDetectionService


class Command(BaseCommand):
    help = 'Run fraud detection analysis on farms to detect off-platform sales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--farm-id',
            type=str,
            help='Analyze a specific farm by ID',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to analyze (default: 30)',
        )
        parser.add_argument(
            '--min-risk',
            type=str,
            choices=['CLEAN', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
            default='LOW',
            help='Minimum risk level to display (default: LOW)',
        )
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Only analyze active farms',
        )
        parser.add_argument(
            '--save-all',
            action='store_true',
            help='Save alerts for all farms even if CLEAN',
        )

    def handle(self, *args, **options):
        farm_id = options.get('farm_id')
        days = options.get('days')
        min_risk = options.get('min_risk')
        active_only = options.get('active_only')
        save_all = options.get('save_all')

        # Risk level ordering
        risk_levels = {
            'CLEAN': 0,
            'LOW': 1,
            'MEDIUM': 2,
            'HIGH': 3,
            'CRITICAL': 4,
        }
        min_risk_level = risk_levels[min_risk]

        # Determine which farms to analyze
        if farm_id:
            try:
                farms = Farm.objects.filter(id=farm_id)
                if not farms.exists():
                    raise CommandError(f'Farm with ID {farm_id} not found')
            except ValueError:
                raise CommandError(f'Invalid farm ID: {farm_id}')
        else:
            farms = Farm.objects.all()
            if active_only:
                farms = farms.filter(is_active=True)

        total_farms = farms.count()
        self.stdout.write(self.style.SUCCESS(f'\n🔍 Starting fraud detection scan...\n'))
        self.stdout.write(f'📊 Analyzing {total_farms} farm(s) over the last {days} days\n')
        self.stdout.write(f'⚠️  Showing alerts with risk level: {min_risk}+\n')
        self.stdout.write('─' * 80 + '\n')

        # Statistics
        stats = {
            'total': 0,
            'clean': 0,
            'low': 0,
            'medium': 0,
            'high': 0,
            'critical': 0,
            'analyzed': 0,
        }

        # Analyze each farm
        for farm in farms:
            stats['analyzed'] += 1
            
            # Run detection
            try:
                detector_instance = FraudDetectionService(farm)
                alert = detector_instance.run_full_analysis(days=days, save=True)
                
                if not alert:
                    stats['clean'] += 1
                    if save_all:
                        # Create a CLEAN alert for record keeping
                        FraudAlert.objects.create(
                            farm=farm,
                            risk_score=0,
                            risk_level='CLEAN',
                            alerts=[],
                            status='false_positive',
                            review_notes='No fraud indicators detected (auto-reviewed)',
                            reviewed_at=timezone.now(),
                            analysis_period_days=days,
                        )
                    continue

                # Count by risk level
                stats['total'] += 1
                stats[alert.risk_level.lower()] += 1

                # Only display if meets minimum risk threshold
                if risk_levels[alert.risk_level] >= min_risk_level:
                    self._display_alert(farm, alert)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error analyzing farm {farm.id} ({farm.farm_name}): {str(e)}')
                )
                continue

        # Display summary
        self.stdout.write('\n' + '─' * 80)
        self.stdout.write(self.style.SUCCESS(f'\n📈 FRAUD DETECTION SUMMARY\n'))
        self.stdout.write(f'Farms analyzed: {stats["analyzed"]}')
        self.stdout.write(f'Alerts generated: {stats["total"]}')
        self.stdout.write(f'  • 🟢 Clean: {stats["clean"]}')
        self.stdout.write(f'  • 🟡 Low risk: {stats["low"]}')
        self.stdout.write(f'  • 🟠 Medium risk: {stats["medium"]}')
        self.stdout.write(f'  • 🔴 High risk: {stats["high"]}')
        self.stdout.write(f'  • 🚨 Critical risk: {stats["critical"]}')
        
        # Recommendations
        if stats['critical'] > 0:
            self.stdout.write(
                self.style.ERROR(f'\n🚨 URGENT: {stats["critical"]} farm(s) require immediate investigation!')
            )
        elif stats['high'] > 0:
            self.stdout.write(
                self.style.WARNING(f'\n⚠️  WARNING: {stats["high"]} farm(s) should be audited soon.')
            )
        elif stats['medium'] > 0:
            self.stdout.write(f'\n💡 INFO: {stats["medium"]} farm(s) warrant monitoring.')
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ No significant fraud indicators detected.'))

        self.stdout.write('\n' + '─' * 80 + '\n')

    def _display_alert(self, farm, alert):
        """Display a formatted fraud alert"""
        # Risk level styling
        risk_styles = {
            'CLEAN': self.style.SUCCESS,
            'LOW': lambda x: self.style.WARNING(x),
            'MEDIUM': lambda x: self.style.WARNING(x),
            'HIGH': self.style.ERROR,
            'CRITICAL': self.style.ERROR,
        }
        risk_icons = {
            'CLEAN': '🟢',
            'LOW': '🟡',
            'MEDIUM': '🟠',
            'HIGH': '🔴',
            'CRITICAL': '🚨',
        }

        style = risk_styles.get(alert.risk_level, lambda x: x)
        icon = risk_icons.get(alert.risk_level, '⚠️')

        # Header
        self.stdout.write(f'\n{icon} Farm: {farm.farm_name} (ID: {farm.id})')
        self.stdout.write(style(f'   Risk Level: {alert.risk_level} (Score: {alert.risk_score}/100)'))
        self.stdout.write(f'   Farmer: {farm.user.get_full_name()} ({farm.user.phone})')
        
        # Alerts
        if alert.alerts:
            self.stdout.write(f'   Alerts ({len(alert.alerts)}):')
            for i, fraud_alert in enumerate(alert.alerts, 1):
                severity = fraud_alert.get('severity', 'MEDIUM')
                severity_icon = risk_icons.get(severity, '⚠️')
                self.stdout.write(
                    f'      {i}. {severity_icon} {fraud_alert.get("type", "Unknown")}: '
                    f'{fraud_alert.get("message", "No details")}'
                )
                
                # Show details if available
                details = fraud_alert.get('details', {})
                if details:
                    for key, value in details.items():
                        if isinstance(value, float):
                            self.stdout.write(f'         • {key}: {value:.1f}')
                        else:
                            self.stdout.write(f'         • {key}: {value}')

        # Recommendations
        if alert.risk_level in ['HIGH', 'CRITICAL']:
            self.stdout.write(style(f'   ⚡ Action: Schedule immediate physical audit'))
        elif alert.risk_level == 'MEDIUM':
            self.stdout.write(f'   💡 Action: Monitor closely and verify with customer surveys')
        else:
            self.stdout.write(f'   ✓ Action: Continue normal monitoring')

        self.stdout.write('')  # Blank line
