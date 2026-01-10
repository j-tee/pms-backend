"""
Cloudflare Turnstile CAPTCHA Verification Service

Verifies Turnstile tokens from frontend against Cloudflare API.
Turnstile is free with unlimited requests - perfect for high-volume applications.

Documentation: https://developers.cloudflare.com/turnstile/
"""

import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class TurnstileVerificationError(Exception):
    """Raised when Turnstile verification fails."""
    pass


class TurnstileService:
    """
    Service for verifying Cloudflare Turnstile CAPTCHA tokens.
    
    Usage:
        service = TurnstileService()
        is_valid = service.verify_token(token, user_ip='192.168.1.1')
    """
    
    VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
    
    def __init__(self):
        self.secret_key = getattr(settings, 'TURNSTILE_SECRET_KEY', None)
        self.enabled = getattr(settings, 'TURNSTILE_ENABLED', False)
        
        if self.enabled and not self.secret_key:
            logger.warning(
                "Turnstile is enabled but TURNSTILE_SECRET_KEY is not set. "
                "CAPTCHA verification will fail!"
            )
    
    def verify_token(self, token: str, user_ip: str = None) -> bool:
        """
        Verify a Turnstile token.
        
        Args:
            token: The Turnstile response token from frontend
            user_ip: Optional user IP address for additional verification
        
        Returns:
            True if token is valid, False otherwise
        
        Raises:
            TurnstileVerificationError: If verification request fails
        """
        if not self.enabled:
            logger.info("Turnstile verification disabled - accepting all tokens")
            return True
        
        if not token:
            logger.warning("No Turnstile token provided")
            return False
        
        if not self.secret_key:
            logger.error("TURNSTILE_SECRET_KEY not configured")
            return False
        
        try:
            # Prepare verification request
            payload = {
                'secret': self.secret_key,
                'response': token,
            }
            
            # Include IP if provided (recommended for better security)
            if user_ip:
                payload['remoteip'] = user_ip
            
            # Send verification request to Cloudflare
            response = requests.post(
                self.VERIFY_URL,
                data=payload,
                timeout=10  # 10 second timeout
            )
            
            if response.status_code != 200:
                logger.error(
                    f"Turnstile API returned status {response.status_code}: {response.text}"
                )
                raise TurnstileVerificationError(
                    f"Turnstile API error: {response.status_code}"
                )
            
            result = response.json()
            
            # Check if verification succeeded
            if result.get('success'):
                logger.info("Turnstile token verified successfully")
                return True
            
            # Log error codes for debugging
            error_codes = result.get('error-codes', [])
            logger.warning(f"Turnstile verification failed: {error_codes}")
            
            return False
        
        except requests.exceptions.Timeout:
            logger.error("Turnstile verification timeout")
            # In production, decide: fail open (return True) or fail closed (return False)
            # Failing open allows requests during Cloudflare outages
            # Failing closed is more secure but can block legitimate users
            return False  # Fail closed by default
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Turnstile verification network error: {e}")
            return False  # Fail closed
        
        except Exception as e:
            logger.exception(f"Unexpected error during Turnstile verification: {e}")
            raise TurnstileVerificationError(str(e))
    
    def get_error_message(self, error_codes: list) -> str:
        """
        Convert Turnstile error codes to human-readable messages.
        
        Common error codes:
        - missing-input-secret: Secret key missing
        - invalid-input-secret: Secret key invalid
        - missing-input-response: Token missing
        - invalid-input-response: Token invalid or expired
        - timeout-or-duplicate: Token already used or expired
        """
        error_map = {
            'missing-input-secret': 'Server configuration error',
            'invalid-input-secret': 'Server configuration error',
            'missing-input-response': 'CAPTCHA verification required',
            'invalid-input-response': 'CAPTCHA verification failed. Please try again.',
            'timeout-or-duplicate': 'CAPTCHA expired or already used. Please refresh.',
        }
        
        messages = [error_map.get(code, f'Unknown error: {code}') for code in error_codes]
        return '; '.join(messages)


# Singleton instance
turnstile_service = TurnstileService()
