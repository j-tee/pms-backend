"""
Hubtel SMS Service for Ghana.
Handles SMS sending, delivery tracking, and cost monitoring.

Official Hubtel API Documentation:
https://developers.hubtel.com/documentations/sendmessage
"""
import requests
import logging
from typing import Dict, Optional, List
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)


class HubtelSMSService:
    """
    Service for sending SMS via Hubtel API.
    
    Hubtel is a popular SMS gateway in Ghana with competitive rates
    and reliable delivery tracking.
    """
    
    # Hubtel API endpoints
    BASE_URL = "https://api.hubtel.com/v1/messages/send"
    BALANCE_URL = "https://api.hubtel.com/v1/account/balance"
    
    # SMS cost estimates (in GHS) - Update based on your Hubtel pricing
    SMS_COST_PER_PAGE = Decimal('0.04')  # ~4 pesewas per SMS page
    CHARS_PER_PAGE = 160  # Standard SMS page length
    
    def __init__(self):
        """Initialize Hubtel SMS service with credentials from settings."""
        self.client_id = getattr(settings, 'HUBTEL_CLIENT_ID', None)
        self.client_secret = getattr(settings, 'HUBTEL_CLIENT_SECRET', None)
        self.sender_id = getattr(settings, 'HUBTEL_SENDER_ID', 'YEA-PMS')
        self.enabled = getattr(settings, 'SMS_ENABLED', False)
        
        if not self.client_id or not self.client_secret:
            logger.warning("Hubtel credentials not configured. SMS sending will be simulated.")
    
    def send_sms(
        self,
        phone_number: str,
        message: str,
        reference: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> Dict:
        """
        Send SMS via Hubtel API.
        
        Args:
            phone_number: Recipient phone number (E.164 format: +233XXXXXXXXX)
            message: SMS message content
            reference: Optional reference ID for tracking
            callback_url: Optional webhook URL for delivery reports
        
        Returns:
            dict: Response with status, message_id, cost, and error info
        """
        # Validate phone number format
        if not phone_number.startswith('+233'):
            phone_number = self._normalize_phone_number(phone_number)
        
        # Calculate SMS pages and estimated cost
        pages = self._calculate_sms_pages(message)
        estimated_cost = pages * self.SMS_COST_PER_PAGE
        
        # If SMS is disabled, simulate sending
        if not self.enabled or not self.client_id:
            return self._simulate_sms(phone_number, message, estimated_cost)
        
        # Prepare request payload
        payload = {
            'From': self.sender_id,
            'To': phone_number,
            'Content': message,
            'RegisteredDelivery': True,  # Request delivery reports
        }
        
        if reference:
            payload['ClientReference'] = reference
        
        if callback_url:
            payload['CallbackUrl'] = callback_url
        
        try:
            # Make API request with Basic Auth
            response = requests.post(
                self.BASE_URL,
                json=payload,
                auth=(self.client_id, self.client_secret),
                timeout=10
            )
            
            # Parse response
            if response.status_code == 201:  # Success
                data = response.json()
                
                logger.info(
                    f"SMS sent successfully to {phone_number}. "
                    f"MessageId: {data.get('MessageId')}, Cost: GHS {estimated_cost}"
                )
                
                return {
                    'success': True,
                    'message_id': data.get('MessageId'),
                    'status': data.get('Status'),
                    'rate': data.get('Rate', float(estimated_cost)),
                    'network_id': data.get('NetworkId'),
                    'phone_number': phone_number,
                    'pages': pages,
                    'timestamp': timezone.now().isoformat(),
                }
            
            else:
                # Handle error response
                error_data = response.json() if response.content else {}
                error_message = error_data.get('Message', 'Unknown error')
                
                logger.error(
                    f"Failed to send SMS to {phone_number}. "
                    f"Status: {response.status_code}, Error: {error_message}"
                )
                
                return {
                    'success': False,
                    'error': error_message,
                    'status_code': response.status_code,
                    'phone_number': phone_number,
                    'timestamp': timezone.now().isoformat(),
                }
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout sending SMS to {phone_number}")
            return {
                'success': False,
                'error': 'Request timeout',
                'phone_number': phone_number,
                'timestamp': timezone.now().isoformat(),
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending SMS to {phone_number}: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'phone_number': phone_number,
                'timestamp': timezone.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Unexpected error sending SMS to {phone_number}: {str(e)}")
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}',
                'phone_number': phone_number,
                'timestamp': timezone.now().isoformat(),
            }
    
    def send_bulk_sms(
        self,
        recipients: List[Dict[str, str]],
        callback_url: Optional[str] = None
    ) -> Dict:
        """
        Send SMS to multiple recipients.
        
        Args:
            recipients: List of dicts with 'phone' and 'message' keys
            callback_url: Optional webhook URL for delivery reports
        
        Returns:
            dict: Summary of sent messages with success/failure counts
        """
        results = {
            'total': len(recipients),
            'successful': 0,
            'failed': 0,
            'total_cost': Decimal('0.00'),
            'messages': []
        }
        
        for recipient in recipients:
            phone = recipient.get('phone')
            message = recipient.get('message')
            reference = recipient.get('reference')
            
            if not phone or not message:
                results['failed'] += 1
                continue
            
            response = self.send_sms(
                phone_number=phone,
                message=message,
                reference=reference,
                callback_url=callback_url
            )
            
            results['messages'].append(response)
            
            if response.get('success'):
                results['successful'] += 1
                results['total_cost'] += Decimal(str(response.get('rate', 0)))
            else:
                results['failed'] += 1
        
        logger.info(
            f"Bulk SMS sent: {results['successful']}/{results['total']} successful, "
            f"Total cost: GHS {results['total_cost']:.2f}"
        )
        
        return results
    
    def get_account_balance(self) -> Dict:
        """
        Get current Hubtel account balance.
        
        Returns:
            dict: Balance information
        """
        if not self.enabled or not self.client_id:
            return {
                'success': False,
                'error': 'Hubtel not configured',
            }
        
        try:
            response = requests.get(
                self.BALANCE_URL,
                auth=(self.client_id, self.client_secret),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'balance': data.get('Balance', 0),
                    'currency': data.get('Currency', 'GHS'),
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to fetch balance',
                    'status_code': response.status_code,
                }
        
        except Exception as e:
            logger.error(f"Error fetching account balance: {str(e)}")
            return {
                'success': False,
                'error': str(e),
            }
    
    def _normalize_phone_number(self, phone: str) -> str:
        """
        Normalize Ghanaian phone number to E.164 format.
        
        Examples:
            0244123456 -> +233244123456
            244123456 -> +233244123456
            +233244123456 -> +233244123456
        """
        # Remove spaces, dashes, and parentheses
        phone = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Remove leading zeros
        phone = phone.lstrip('0')
        
        # Add Ghana country code if not present
        if not phone.startswith('+233') and not phone.startswith('233'):
            phone = f'+233{phone}'
        elif phone.startswith('233'):
            phone = f'+{phone}'
        
        return phone
    
    def _calculate_sms_pages(self, message: str) -> int:
        """
        Calculate number of SMS pages required for message.
        
        Standard SMS:
        - 1 page = 160 characters (GSM-7)
        - 1 page = 70 characters (Unicode/special chars)
        
        Concatenated SMS:
        - Each part = 153 characters (GSM-7)
        - Each part = 67 characters (Unicode)
        """
        # Check if message contains Unicode characters
        try:
            message.encode('gsm0338')
            is_unicode = False
        except (UnicodeEncodeError, LookupError):
            is_unicode = True
        
        message_length = len(message)
        
        if message_length == 0:
            return 0
        
        if is_unicode:
            # Unicode SMS
            if message_length <= 70:
                return 1
            else:
                return (message_length + 66) // 67
        else:
            # GSM-7 SMS
            if message_length <= 160:
                return 1
            else:
                return (message_length + 152) // 153
    
    def _simulate_sms(self, phone_number: str, message: str, cost: Decimal) -> Dict:
        """Simulate SMS sending for development/testing."""
        logger.info(
            f"\n{'='*60}\n"
            f"📱 SIMULATED SMS\n"
            f"To: {phone_number}\n"
            f"Message: {message}\n"
            f"Estimated Cost: GHS {cost:.4f}\n"
            f"{'='*60}\n"
        )
        
        return {
            'success': True,
            'message_id': f'SIM-{timezone.now().timestamp():.0f}',
            'status': 'simulated',
            'rate': float(cost),
            'network_id': 'SIMULATION',
            'phone_number': phone_number,
            'pages': self._calculate_sms_pages(message),
            'timestamp': timezone.now().isoformat(),
            'simulated': True,
        }


# Singleton instance
_hubtel_service = None


def get_sms_service() -> HubtelSMSService:
    """Get or create singleton SMS service instance."""
    global _hubtel_service
    if _hubtel_service is None:
        _hubtel_service = HubtelSMSService()
    return _hubtel_service
