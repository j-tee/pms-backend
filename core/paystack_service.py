"""
Paystack Payment Service

Handles all Paystack API interactions for:
- Mobile Money (MoMo) payments for marketplace subscription fees
- Payment initialization and verification
- Webhook signature verification
- Refunds and reversals

Supported MoMo Providers (Ghana):
- MTN Mobile Money
- Vodafone Cash
- AirtelTigo Money
- Telecel Cash

Documentation: https://paystack.com/docs/api/
"""

import hashlib
import hmac
import logging
import requests
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class PaystackError(Exception):
    """Base exception for Paystack errors"""
    def __init__(self, message: str, code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code or 'PAYSTACK_ERROR'
        self.details = details or {}


class PaystackService:
    """
    Paystack Payment Gateway Service
    
    Usage:
        from core.paystack_service import PaystackService
        
        # Initialize MoMo payment
        result = PaystackService.initialize_momo_payment(
            amount=5000,  # GHS 50.00 (amount in pesewas)
            email="farmer@example.com",
            phone="0241234567",
            provider="mtn",
            reference="SUB-2026-01-12345",
            metadata={"subscription_id": "uuid-here"}
        )
        
        # Verify payment
        verified = PaystackService.verify_transaction(reference)
    """
    
    BASE_URL = settings.PAYSTACK_BASE_URL
    SECRET_KEY = settings.PAYSTACK_SECRET_KEY
    PUBLIC_KEY = settings.PAYSTACK_PUBLIC_KEY
    WEBHOOK_SECRET = settings.PAYSTACK_WEBHOOK_SECRET
    CURRENCY = settings.PAYSTACK_CURRENCY
    
    # Mobile Money provider codes for Ghana
    MOMO_PROVIDERS = {
        'mtn': 'mtn',
        'vodafone': 'vod',
        'airteltigo': 'tgo',
        'telecel': 'tgo',  # Telecel uses same code as AirtelTigo
    }
    
    # Provider names for display
    MOMO_PROVIDER_NAMES = {
        'mtn': 'MTN Mobile Money',
        'vodafone': 'Vodafone Cash',
        'airteltigo': 'AirtelTigo Money',
        'telecel': 'Telecel Cash',
    }
    
    @classmethod
    def _get_headers(cls) -> Dict[str, str]:
        """Get authorization headers for Paystack API"""
        return {
            'Authorization': f'Bearer {cls.SECRET_KEY}',
            'Content-Type': 'application/json',
        }
    
    @classmethod
    def _make_request(
        cls, 
        method: str, 
        endpoint: str, 
        data: dict = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Paystack API
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /transaction/initialize)
            data: Request payload
            
        Returns:
            Parsed JSON response
            
        Raises:
            PaystackError: On API errors
        """
        url = f"{cls.BASE_URL}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=cls._get_headers(),
                json=data,
                timeout=30
            )
            
            result = response.json()
            
            if not response.ok or not result.get('status'):
                error_message = result.get('message', 'Unknown Paystack error')
                logger.error(f"Paystack API error: {error_message}", extra={
                    'endpoint': endpoint,
                    'status_code': response.status_code,
                    'response': result
                })
                raise PaystackError(
                    message=error_message,
                    code='API_ERROR',
                    details={'response': result, 'status_code': response.status_code}
                )
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"Paystack API timeout: {endpoint}")
            raise PaystackError(
                message="Payment gateway timeout. Please try again.",
                code='TIMEOUT'
            )
        except requests.exceptions.ConnectionError:
            logger.error(f"Paystack API connection error: {endpoint}")
            raise PaystackError(
                message="Unable to connect to payment gateway. Please try again.",
                code='CONNECTION_ERROR'
            )
        except Exception as e:
            if isinstance(e, PaystackError):
                raise
            logger.exception(f"Unexpected Paystack error: {e}")
            raise PaystackError(
                message="An unexpected error occurred. Please try again.",
                code='UNEXPECTED_ERROR',
                details={'error': str(e)}
            )
    
    @classmethod
    def initialize_momo_payment(
        cls,
        amount: int,
        email: str,
        phone: str,
        provider: str,
        reference: str,
        metadata: dict = None,
        callback_url: str = None
    ) -> Dict[str, Any]:
        """
        Initialize a Mobile Money payment
        
        Args:
            amount: Amount in pesewas (GHS 50 = 5000 pesewas)
            email: Customer email (required by Paystack)
            phone: Customer phone number (format: 0241234567)
            provider: MoMo provider (mtn, vodafone, airteltigo, telecel)
            reference: Unique payment reference
            metadata: Additional data to attach to transaction
            callback_url: URL to redirect after payment (optional)
            
        Returns:
            Dict with authorization_url, access_code, reference
            
        Raises:
            PaystackError: On initialization failure
        """
        # Normalize phone number (remove +233 prefix if present)
        if phone.startswith('+233'):
            phone = '0' + phone[4:]
        elif phone.startswith('233'):
            phone = '0' + phone[3:]
        
        # Validate provider
        provider_lower = provider.lower()
        if provider_lower not in cls.MOMO_PROVIDERS:
            raise PaystackError(
                message=f"Unsupported mobile money provider: {provider}",
                code='INVALID_PROVIDER',
                details={'supported_providers': list(cls.MOMO_PROVIDERS.keys())}
            )
        
        payload = {
            'amount': amount,
            'email': email,
            'currency': cls.CURRENCY,
            'reference': reference,
            'mobile_money': {
                'phone': phone,
                'provider': cls.MOMO_PROVIDERS[provider_lower]
            },
            'metadata': metadata or {},
            'channels': ['mobile_money'],
        }
        
        if callback_url:
            payload['callback_url'] = callback_url
        
        logger.info(f"Initializing MoMo payment: {reference}, amount: {amount} pesewas")
        
        result = cls._make_request('POST', '/transaction/initialize', payload)
        
        return {
            'status': 'success',
            'authorization_url': result['data'].get('authorization_url'),
            'access_code': result['data'].get('access_code'),
            'reference': result['data'].get('reference'),
            'message': 'Payment initialized successfully. Please authorize on your phone.'
        }
    
    @classmethod
    def charge_mobile_money(
        cls,
        amount: int,
        email: str,
        phone: str,
        provider: str,
        reference: str,
        metadata: dict = None
    ) -> Dict[str, Any]:
        """
        Directly charge a mobile money account (USSD prompt sent to phone)
        
        This initiates a direct charge where customer receives a USSD prompt
        on their phone to authorize the payment.
        
        Args:
            amount: Amount in pesewas
            email: Customer email
            phone: Customer phone (0241234567 format)
            provider: MoMo provider code
            reference: Unique reference
            metadata: Additional transaction data
            
        Returns:
            Dict with transaction status and reference
        """
        # Normalize phone number
        if phone.startswith('+233'):
            phone = '0' + phone[4:]
        elif phone.startswith('233'):
            phone = '0' + phone[3:]
        
        provider_lower = provider.lower()
        if provider_lower not in cls.MOMO_PROVIDERS:
            raise PaystackError(
                message=f"Unsupported mobile money provider: {provider}",
                code='INVALID_PROVIDER'
            )
        
        payload = {
            'amount': amount,
            'email': email,
            'currency': cls.CURRENCY,
            'reference': reference,
            'mobile_money': {
                'phone': phone,
                'provider': cls.MOMO_PROVIDERS[provider_lower]
            },
            'metadata': metadata or {}
        }
        
        logger.info(f"Charging MoMo: {reference}, amount: {amount} pesewas, provider: {provider}")
        
        result = cls._make_request('POST', '/charge', payload)
        
        data = result['data']
        
        return {
            'status': data.get('status'),
            'reference': data.get('reference'),
            'display_text': data.get('display_text', 'Please authorize payment on your phone'),
            'ussd_code': data.get('ussd_code'),
        }
    
    @classmethod
    def verify_transaction(cls, reference: str) -> Dict[str, Any]:
        """
        Verify a transaction by reference
        
        Args:
            reference: Transaction reference
            
        Returns:
            Dict with transaction details and status
        """
        logger.info(f"Verifying transaction: {reference}")
        
        result = cls._make_request('GET', f'/transaction/verify/{reference}')
        
        data = result['data']
        
        return {
            'status': data.get('status'),  # success, failed, pending, abandoned
            'reference': data.get('reference'),
            'amount': data.get('amount'),  # In pesewas
            'amount_ghs': Decimal(data.get('amount', 0)) / 100,  # Convert to GHS
            'currency': data.get('currency'),
            'channel': data.get('channel'),
            'gateway_response': data.get('gateway_response'),
            'paid_at': data.get('paid_at'),
            'transaction_date': data.get('transaction_date'),
            'fees': data.get('fees'),  # Paystack fees in pesewas
            'metadata': data.get('metadata', {}),
            'authorization': data.get('authorization', {}),
            'customer': data.get('customer', {}),
        }
    
    @classmethod
    def get_transaction(cls, transaction_id: str) -> Dict[str, Any]:
        """
        Fetch transaction details by Paystack transaction ID
        
        Args:
            transaction_id: Paystack transaction ID
            
        Returns:
            Transaction details
        """
        result = cls._make_request('GET', f'/transaction/{transaction_id}')
        return result['data']
    
    @classmethod
    def submit_otp(cls, reference: str, otp: str) -> Dict[str, Any]:
        """
        Submit OTP for transactions that require it
        
        Args:
            reference: Transaction reference
            otp: One-time password from customer
            
        Returns:
            Transaction status after OTP submission
        """
        payload = {
            'reference': reference,
            'otp': otp
        }
        
        result = cls._make_request('POST', '/charge/submit_otp', payload)
        return result['data']
    
    @classmethod
    def check_pending_charge(cls, reference: str) -> Dict[str, Any]:
        """
        Check status of a pending charge
        
        Args:
            reference: Transaction reference
            
        Returns:
            Current charge status
        """
        payload = {'reference': reference}
        result = cls._make_request('POST', '/charge/check_pending', payload)
        return result['data']
    
    @classmethod
    def refund_transaction(
        cls,
        transaction_reference: str,
        amount: int = None,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        Initiate a refund for a transaction
        
        Args:
            transaction_reference: Original transaction reference
            amount: Amount to refund in pesewas (None = full refund)
            reason: Reason for refund
            
        Returns:
            Refund status
        """
        payload = {'transaction': transaction_reference}
        
        if amount:
            payload['amount'] = amount
        if reason:
            payload['merchant_note'] = reason
        
        logger.info(f"Initiating refund for: {transaction_reference}")
        
        result = cls._make_request('POST', '/refund', payload)
        return result['data']
    
    @classmethod
    def verify_webhook_signature(
        cls,
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify Paystack webhook signature
        
        Args:
            payload: Raw request body (bytes)
            signature: X-Paystack-Signature header value
            
        Returns:
            True if signature is valid
        """
        if not cls.WEBHOOK_SECRET:
            logger.warning("PAYSTACK_WEBHOOK_SECRET not configured!")
            return False
        
        expected_signature = hmac.new(
            cls.WEBHOOK_SECRET.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    @classmethod
    def get_banks(cls, country: str = 'ghana') -> list:
        """
        Get list of supported banks for a country
        
        Args:
            country: Country code (ghana, nigeria, etc.)
            
        Returns:
            List of bank objects with name, code, etc.
        """
        result = cls._make_request('GET', f'/bank?country={country}')
        return result['data']
    
    @classmethod
    def resolve_account_number(
        cls,
        account_number: str,
        bank_code: str
    ) -> Dict[str, Any]:
        """
        Resolve bank account to get account name
        
        Args:
            account_number: Bank account number
            bank_code: Bank code from get_banks()
            
        Returns:
            Dict with account_name, account_number, bank_id
        """
        result = cls._make_request(
            'GET',
            f'/bank/resolve?account_number={account_number}&bank_code={bank_code}'
        )
        return result['data']
    
    @classmethod
    def generate_payment_reference(cls, prefix: str = 'SUB') -> str:
        """
        Generate a unique payment reference
        
        Format: {PREFIX}-{YYYYMMDD}-{RANDOM}
        Example: SUB-20260105-A3B4C5D6
        
        Args:
            prefix: Reference prefix
            
        Returns:
            Unique reference string
        """
        import secrets
        date_str = timezone.now().strftime('%Y%m%d')
        random_part = secrets.token_hex(4).upper()
        return f"{prefix}-{date_str}-{random_part}"
    
    @classmethod
    def convert_to_pesewas(cls, amount_ghs: Decimal) -> int:
        """
        Convert GHS amount to pesewas (smallest unit)
        
        Args:
            amount_ghs: Amount in Ghana Cedis
            
        Returns:
            Amount in pesewas (100 pesewas = 1 GHS)
        """
        return int(amount_ghs * 100)
    
    @classmethod
    def convert_to_ghs(cls, amount_pesewas: int) -> Decimal:
        """
        Convert pesewas to GHS
        
        Args:
            amount_pesewas: Amount in pesewas
            
        Returns:
            Amount in GHS
        """
        return Decimal(amount_pesewas) / 100
    
    @classmethod
    def get_momo_provider_from_phone(cls, phone: str) -> Optional[str]:
        """
        Attempt to detect MoMo provider from phone number prefix
        
        Ghana Mobile Network Prefixes:
        - MTN: 024, 054, 055, 059
        - Vodafone: 020, 050
        - AirtelTigo: 026, 027, 056, 057
        
        Args:
            phone: Phone number
            
        Returns:
            Provider name or None if unknown
        """
        # Normalize phone number
        if phone.startswith('+233'):
            phone = '0' + phone[4:]
        elif phone.startswith('233'):
            phone = '0' + phone[3:]
        
        prefix = phone[:3]
        
        mtn_prefixes = ['024', '054', '055', '059']
        vodafone_prefixes = ['020', '050']
        airteltigo_prefixes = ['026', '027', '056', '057']
        
        if prefix in mtn_prefixes:
            return 'mtn'
        elif prefix in vodafone_prefixes:
            return 'vodafone'
        elif prefix in airteltigo_prefixes:
            return 'airteltigo'
        
        return None
