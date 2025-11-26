"""
Spam Detection Service

Automated spam detection for registration applications.
Calculates spam scores and identifies potential spam indicators.
"""

import re
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


class SpamDetectionService:
    """
    Service for detecting spam/bot registrations.
    Returns spam score (0-100) and list of flags.
    """
    
    # Common spam patterns
    SPAM_KEYWORDS = [
        'test', 'demo', 'fake', 'spam', 'bot', 'dummy',
        'asdf', 'qwerty', '12345', 'aaaaa', 'xxxxx'
    ]
    
    SUSPICIOUS_EMAIL_DOMAINS = [
        'tempmail.com', 'guerrillamail.com', 'mailinator.com',
        '10minutemail.com', 'throwaway.email', 'yopmail.com'
    ]
    
    def __init__(self, registration_data):
        """
        Initialize with registration data dictionary.
        
        Expected keys:
        - farm_name
        - email
        - phone_number
        - ghana_card_number
        - first_name
        - last_name
        - ip_address (optional)
        """
        self.data = registration_data
        self.spam_score = Decimal('0.00')
        self.flags = []
    
    def analyze(self):
        """
        Run all spam detection checks.
        Returns (spam_score: Decimal, flags: list)
        """
        self.spam_score = Decimal('0.00')
        self.flags = []
        
        # Run all checks
        self._check_farm_name()
        self._check_email()
        self._check_personal_names()
        self._check_ghana_card()
        self._check_suspicious_patterns()
        self._check_data_consistency()
        
        return self.spam_score, self.flags
    
    def _add_flag(self, flag, score_increase):
        """Add a spam flag and increase score"""
        self.flags.append(flag)
        self.spam_score += Decimal(str(score_increase))
    
    def _check_farm_name(self):
        """Check farm name for spam patterns"""
        farm_name = self.data.get('farm_name', '').lower()
        
        if not farm_name or len(farm_name) < 5:
            self._add_flag('farm_name_too_short', 15)
        
        # Check for spam keywords
        for keyword in self.SPAM_KEYWORDS:
            if keyword in farm_name:
                self._add_flag(f'farm_name_contains_{keyword}', 25)
                break
        
        # Check for repetitive characters (e.g., "aaaaa", "11111")
        if re.search(r'(.)\1{4,}', farm_name):
            self._add_flag('farm_name_repetitive_characters', 20)
        
        # Check for random gibberish (no vowels or all consonants)
        vowels = set('aeiou')
        has_vowels = any(c in vowels for c in farm_name)
        if len(farm_name) > 5 and not has_vowels:
            self._add_flag('farm_name_no_vowels', 15)
    
    def _check_email(self):
        """Check email for suspicious patterns"""
        email = self.data.get('email', '').lower()
        
        if not email:
            # Email is optional, so no flag if missing
            return
        
        # Check for temporary/disposable email domains
        domain = email.split('@')[-1] if '@' in email else ''
        if domain in self.SUSPICIOUS_EMAIL_DOMAINS:
            self._add_flag('disposable_email_domain', 30)
        
        # Check for random email patterns (lots of numbers)
        local_part = email.split('@')[0] if '@' in email else email
        digit_count = sum(c.isdigit() for c in local_part)
        if len(local_part) > 0 and (digit_count / len(local_part)) > 0.7:
            self._add_flag('email_mostly_numbers', 15)
    
    def _check_personal_names(self):
        """Check first/last names for spam patterns"""
        first_name = self.data.get('first_name', '').lower()
        last_name = self.data.get('last_name', '').lower()
        
        # Check for spam keywords in names
        for keyword in self.SPAM_KEYWORDS:
            if keyword in first_name or keyword in last_name:
                self._add_flag('name_contains_spam_keyword', 25)
                break
        
        # Check for repetitive names (e.g., "John John")
        if first_name and last_name and first_name == last_name:
            self._add_flag('first_last_name_identical', 20)
        
        # Check for single character names
        if len(first_name) == 1 or len(last_name) == 1:
            self._add_flag('single_character_name', 15)
    
    def _check_ghana_card(self):
        """Check Ghana Card number for suspicious patterns"""
        ghana_card = self.data.get('ghana_card_number', '')
        
        # Check format (should be GHA-XXXXXXXXX-X)
        if not re.match(r'^GHA-\d{9}-\d$', ghana_card):
            self._add_flag('invalid_ghana_card_format', 20)
        
        # Check for repetitive numbers
        digits = ''.join(filter(str.isdigit, ghana_card))
        if digits and re.search(r'(\d)\1{5,}', digits):
            self._add_flag('ghana_card_repetitive_numbers', 15)
    
    def _check_suspicious_patterns(self):
        """Check for other suspicious patterns"""
        # Check if farm name matches personal name exactly
        farm_name = self.data.get('farm_name', '').lower()
        first_name = self.data.get('first_name', '').lower()
        last_name = self.data.get('last_name', '').lower()
        
        full_name = f"{first_name} {last_name}".strip()
        if farm_name == full_name:
            self._add_flag('farm_name_matches_personal_name', 10)
        
        # Check for sequential numbers (12345, 67890)
        all_text = ' '.join([
            str(self.data.get('farm_name', '')),
            str(self.data.get('first_name', '')),
            str(self.data.get('last_name', ''))
        ])
        if re.search(r'12345|23456|34567|45678|56789|67890', all_text):
            self._add_flag('sequential_numbers_detected', 20)
    
    def _check_data_consistency(self):
        """Check for data consistency issues"""
        # Check if multiple fields are empty
        required_fields = ['farm_name', 'first_name', 'last_name', 'ghana_card_number']
        empty_count = sum(1 for field in required_fields if not self.data.get(field))
        
        if empty_count >= 2:
            self._add_flag('multiple_empty_fields', 25)
    
    @classmethod
    def check_registration(cls, registration_data):
        """
        Convenience method to analyze registration data.
        Returns (spam_score: Decimal, flags: list)
        """
        detector = cls(registration_data)
        return detector.analyze()


class RateLimitService:
    """
    Service for checking and enforcing rate limits.
    """
    
    @staticmethod
    def check_rate_limit(ip_address):
        """
        Check if IP address is rate limited.
        Returns (is_allowed: bool, message: str)
        """
        from farms.invitation_models import RegistrationRateLimit
        
        # Get or create rate limit record
        rate_limit, created = RegistrationRateLimit.objects.get_or_create(
            ip_address=ip_address
        )
        
        # Reset if expired
        if not created:
            rate_limit.reset_if_expired()
        
        # Check if blocked
        if rate_limit.is_currently_blocked:
            time_remaining = rate_limit.blocked_until - timezone.now()
            hours_remaining = int(time_remaining.total_seconds() / 3600)
            return False, f"Too many registration attempts. Please try again in {hours_remaining} hours."
        
        # Check daily limit
        if rate_limit.registration_attempts >= 3:
            rate_limit.increment_attempts()
            return False, "Daily registration limit reached (3 registrations per day). Please try again tomorrow."
        
        return True, "Rate limit check passed"
    
    @staticmethod
    def record_attempt(ip_address):
        """Record a registration attempt"""
        from farms.invitation_models import RegistrationRateLimit
        
        rate_limit, created = RegistrationRateLimit.objects.get_or_create(
            ip_address=ip_address
        )
        rate_limit.increment_attempts()
        return rate_limit


class VerificationService:
    """
    Service for email/phone verification.
    """
    
    @staticmethod
    def send_email_verification(user, email):
        """
        Send email verification code.
        Returns (token: VerificationToken, success: bool, message: str)
        """
        from farms.invitation_models import VerificationToken
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Create verification token
        token = VerificationToken.objects.create(
            user=user,
            token_type='email',
            target_value=email,
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        try:
            # Send email
            subject = "Verify Your Email - Poultry Management System"
            message = f"""
            Dear Farmer,
            
            Thank you for registering with the Poultry Management System.
            
            Your email verification code is: {token.token}
            
            This code will expire in 10 minutes.
            
            If you did not request this verification, please ignore this email.
            
            Best regards,
            PMS Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return token, True, "Verification code sent to your email"
        
        except Exception as e:
            return token, False, f"Failed to send email: {str(e)}"
    
    @staticmethod
    def send_phone_verification(user, phone_number):
        """
        Send SMS verification code.
        Returns (token: VerificationToken, success: bool, message: str)
        """
        from farms.invitation_models import VerificationToken
        from core.sms_service import send_sms
        
        # Create verification token
        token = VerificationToken.objects.create(
            user=user,
            token_type='phone',
            target_value=str(phone_number),
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        try:
            # Send SMS
            message = f"Your PMS verification code is: {token.token}. Valid for 10 minutes."
            
            success, result = send_sms(
                phone_number=str(phone_number),
                message=message
            )
            
            if success:
                return token, True, "Verification code sent via SMS"
            else:
                return token, False, f"Failed to send SMS: {result}"
        
        except Exception as e:
            return token, False, f"Failed to send SMS: {str(e)}"
    
    @staticmethod
    def verify_token(user, token_type, submitted_code):
        """
        Verify a token code.
        Returns (success: bool, message: str)
        """
        from farms.invitation_models import VerificationToken
        
        # Get latest pending token
        token = VerificationToken.objects.filter(
            user=user,
            token_type=token_type,
            status='pending'
        ).order_by('-created_at').first()
        
        if not token:
            return False, "No verification code found. Please request a new one."
        
        return token.verify(submitted_code)
