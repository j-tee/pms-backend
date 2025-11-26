"""
Management command to test Hubtel SMS integration.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from core.sms_service import get_sms_service
from procurement.services.notification_service import get_notification_service


class Command(BaseCommand):
    help = 'Test Hubtel SMS service configuration and sending'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Test phone number (e.g., +233244123456)',
        )
        parser.add_argument(
            '--test-all',
            action='store_true',
            help='Test all notification types',
        )
        parser.add_argument(
            '--check-balance',
            action='store_true',
            help='Check Hubtel account balance',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== HUBTEL SMS SERVICE TEST ===\n'))
        
        # Display configuration
        self.show_configuration()
        
        # Check balance if requested
        if options['check_balance']:
            self.check_balance()
        
        # Test SMS sending
        phone = options.get('phone')
        if phone:
            self.test_sms_sending(phone)
        
        # Test all notification types
        if options['test_all']:
            if not phone:
                self.stdout.write(self.style.ERROR('Error: --phone required for --test-all'))
                return
            self.test_all_notifications(phone)
        
        self.stdout.write(self.style.SUCCESS('\n=== TEST COMPLETED ===\n'))

    def show_configuration(self):
        """Display current SMS configuration."""
        self.stdout.write(self.style.NOTICE('Configuration:'))
        
        sms_enabled = getattr(settings, 'SMS_ENABLED', False)
        self.stdout.write(f'  SMS Enabled: {sms_enabled}')
        
        client_id = getattr(settings, 'HUBTEL_CLIENT_ID', '')
        if client_id:
            self.stdout.write(f'  Hubtel Client ID: {client_id[:8]}...')
        else:
            self.stdout.write(self.style.WARNING('  Hubtel Client ID: Not configured'))
        
        client_secret = getattr(settings, 'HUBTEL_CLIENT_SECRET', '')
        if client_secret:
            self.stdout.write(f'  Hubtel Client Secret: {client_secret[:8]}...')
        else:
            self.stdout.write(self.style.WARNING('  Hubtel Client Secret: Not configured'))
        
        sender_id = getattr(settings, 'HUBTEL_SENDER_ID', 'YEA-PMS')
        self.stdout.write(f'  Sender ID: {sender_id}')
        
        sms_provider = getattr(settings, 'SMS_PROVIDER', 'console')
        self.stdout.write(f'  Provider: {sms_provider}')
        
        if not sms_enabled or not client_id or not client_secret:
            self.stdout.write(self.style.WARNING('\n⚠ SMS is not fully configured. Messages will be simulated.\n'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ SMS is fully configured.\n'))

    def check_balance(self):
        """Check Hubtel account balance."""
        self.stdout.write(self.style.NOTICE('\nChecking account balance...'))
        
        sms_service = get_sms_service()
        result = sms_service.get_account_balance()
        
        if result.get('success'):
            balance = result.get('balance', 0)
            currency = result.get('currency', 'GHS')
            self.stdout.write(self.style.SUCCESS(f'  Balance: {currency} {balance:.2f}'))
        else:
            error = result.get('error', 'Unknown error')
            self.stdout.write(self.style.ERROR(f'  Error: {error}'))

    def test_sms_sending(self, phone):
        """Test basic SMS sending."""
        self.stdout.write(self.style.NOTICE(f'\nTesting SMS sending to {phone}...'))
        
        sms_service = get_sms_service()
        
        message = (
            "YEA PMS: Test message from Hubtel SMS service.\n"
            "If you receive this, the integration is working! ✓"
        )
        
        result = sms_service.send_sms(
            phone_number=phone,
            message=message,
            reference='TEST-SMS'
        )
        
        if result.get('success'):
            self.stdout.write(self.style.SUCCESS('  ✓ SMS sent successfully!'))
            self.stdout.write(f'    Message ID: {result.get("message_id")}')
            self.stdout.write(f'    Status: {result.get("status")}')
            self.stdout.write(f'    Cost: GHS {result.get("rate", 0):.4f}')
            self.stdout.write(f'    Pages: {result.get("pages")}')
            if result.get('simulated'):
                self.stdout.write(self.style.WARNING('    (Simulated - not actually sent)'))
        else:
            error = result.get('error', 'Unknown error')
            self.stdout.write(self.style.ERROR(f'  ✗ Failed: {error}'))

    def test_all_notifications(self, phone):
        """Test all notification message templates."""
        self.stdout.write(self.style.NOTICE('\nTesting notification templates...'))
        
        sms_service = get_sms_service()
        
        templates = [
            (
                "Farm Assignment",
                "YEA PMS: New order assigned!\n"
                "Order: ORD-2025-00001\n"
                "Quantity: 5,000 birds\n"
                "Type: Broilers\n"
                "Deadline: 15 Nov 2025\n"
                "Please respond within 24 hours."
            ),
            (
                "Assignment Accepted",
                "YEA PMS: Assignment accepted!\n"
                "Farm: Nkwanta Poultry Farm\n"
                "Order: ORD-2025-00001\n"
                "Quantity: 5,000 birds\n"
                "Expected ready: 15 Nov 2025"
            ),
            (
                "Ready for Delivery",
                "YEA PMS: Order ready for delivery!\n"
                "Farm: Nkwanta Poultry Farm\n"
                "Order: ORD-2025-00001\n"
                "Quantity: 5,000 birds\n"
                "Ready since: 14 Nov 2025\n"
                "Schedule pickup ASAP."
            ),
            (
                "Delivery Confirmed",
                "YEA PMS: Delivery confirmed!\n"
                "Order: ORD-2025-00001\n"
                "Quantity: 5,000 birds\n"
                "Quality: PASSED ✓\n"
                "Avg weight: 2.5kg\n"
                "Invoice will be generated soon."
            ),
            (
                "Invoice Generated",
                "YEA PMS: Invoice generated!\n"
                "Invoice: INV-2025-00001\n"
                "Order: ORD-2025-00001\n"
                "Amount: GHS 50,000.00\n"
                "Due date: 30 Nov 2025"
            ),
            (
                "Payment Processed",
                "YEA PMS: Payment processed! 💰\n"
                "Invoice: INV-2025-00001\n"
                "Amount paid: GHS 50,000.00\n"
                "Payment date: 28 Nov 2025\n"
                "Reference: PAY-2025-00001\n"
                "Thank you for your service!"
            ),
            (
                "Farm Approved",
                "YEA PMS: Congratulations! 🎉\n"
                "Your farm 'Nkwanta Poultry Farm' has been APPROVED!\n"
                "Farm ID: F-2025-0001\n"
                "You can now receive procurement orders.\n"
                "Welcome to the YEA Poultry Program!"
            ),
            (
                "Order Overdue",
                "YEA PMS: URGENT - Order overdue!\n"
                "Order: ORD-2025-00001\n"
                "Days overdue: 3\n"
                "Quantity: 5,000 birds\n"
                "Please update status immediately."
            ),
        ]
        
        total_cost = 0
        successful = 0
        
        for title, message in templates:
            self.stdout.write(f'\n  Testing: {title}')
            
            result = sms_service.send_sms(
                phone_number=phone,
                message=message,
                reference=f'TEST-{title.upper().replace(" ", "-")}'
            )
            
            if result.get('success'):
                cost = result.get('rate', 0)
                pages = result.get('pages', 0)
                total_cost += cost
                successful += 1
                self.stdout.write(self.style.SUCCESS(f'    ✓ Sent (Pages: {pages}, Cost: GHS {cost:.4f})'))
            else:
                error = result.get('error', 'Unknown')
                self.stdout.write(self.style.ERROR(f'    ✗ Failed: {error}'))
        
        self.stdout.write(self.style.NOTICE(f'\nSummary:'))
        self.stdout.write(f'  Successful: {successful}/{len(templates)}')
        self.stdout.write(f'  Total cost: GHS {total_cost:.4f}')
