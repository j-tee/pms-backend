"""
Subaccount Manager - Farmer Paystack Subaccount Creation & Management

Creates and manages Paystack subaccounts for farmers to enable direct settlements
to their mobile money or bank accounts.
"""

import logging
from typing import Dict, Optional
from django.utils import timezone
from django.db import transaction

from farms.models import Farm
from .paystack_service import PaystackService, PaystackAPIError


logger = logging.getLogger(__name__)


class SubaccountManager:
    """
    Manages Paystack subaccounts for farmers.
    
    A subaccount allows money to be automatically settled directly to the farmer's
    mobile money or bank account without the platform holding the funds.
    
    Features:
    - Create subaccount with mobile money or bank account
    - Update subaccount details
    - Activate/deactivate subaccounts
    - Validate account information
    """
    
    def __init__(self):
        self.paystack = PaystackService()
    
    @transaction.atomic
    def create_subaccount(self, farm: Farm) -> Dict:
        """
        Create Paystack subaccount for farmer.
        
        The subaccount enables direct settlement of sales revenue to the farmer's
        mobile money or bank account.
        
        Args:
            farm: Farm instance with payment details
            
        Returns:
            Dict containing subaccount details from Paystack
            
        Raises:
            PaystackAPIError: If subaccount creation fails
            ValueError: If farm doesn't have required payment details
        """
        # Check if subaccount already exists
        if farm.paystack_subaccount_code:
            logger.warning(f"Farm {farm.farm_name} already has subaccount: {farm.paystack_subaccount_code}")
            return self.get_subaccount(farm.paystack_subaccount_code)
        
        # Validate payment details
        settlement_bank, account_number = self._get_settlement_details(farm)
        
        # Prepare subaccount data
        subaccount_data = {
            'business_name': farm.farm_name,
            'settlement_bank': settlement_bank,
            'account_number': account_number,
            'percentage_charge': 0,  # We use transaction_charge instead
            'description': f'Subaccount for {farm.farm_name} (Farm ID: {farm.farm_id or farm.application_id})',
            'primary_contact_email': farm.email if farm.email else None,
            'primary_contact_name': f"{farm.first_name} {farm.last_name}",
            'primary_contact_phone': str(farm.primary_phone),
        }
        
        # Remove None values
        subaccount_data = {k: v for k, v in subaccount_data.items() if v is not None}
        
        try:
            logger.info(f"Creating Paystack subaccount for farm: {farm.farm_name}")
            
            # Call Paystack API
            response = self.paystack.post('/subaccount', subaccount_data)
            
            # Extract subaccount details
            data = response.get('data', {})
            subaccount_code = data.get('subaccount_code')
            subaccount_id = data.get('id')
            
            # Update farm with subaccount details
            farm.paystack_subaccount_code = subaccount_code
            farm.paystack_subaccount_id = str(subaccount_id)
            farm.paystack_settlement_account = account_number
            farm.subaccount_created_at = timezone.now()
            farm.subaccount_active = True
            farm.save(update_fields=[
                'paystack_subaccount_code',
                'paystack_subaccount_id',
                'paystack_settlement_account',
                'subaccount_created_at',
                'subaccount_active',
                'updated_at'
            ])
            
            logger.info(f"Subaccount created successfully: {subaccount_code}")
            
            return data
            
        except PaystackAPIError as e:
            logger.error(f"Failed to create subaccount for {farm.farm_name}: {e.message}")
            raise
    
    def _get_settlement_details(self, farm: Farm) -> tuple:
        """
        Extract settlement bank code and account number from farm.
        
        For mobile money: Maps provider to Paystack bank code
        For bank account: Uses provided bank name and account number
        
        Returns:
            Tuple of (settlement_bank_code, account_number)
            
        Raises:
            ValueError: If no valid payment method found
        """
        # Check for mobile money first (preferred for Ghana)
        if farm.mobile_money_number and farm.mobile_money_provider:
            bank_code = self._get_mobile_money_bank_code(farm.mobile_money_provider)
            # Remove country code and formatting from phone number
            account_number = str(farm.mobile_money_number).replace('+233', '0')
            return (bank_code, account_number)
        
        # Check for bank account
        if farm.bank_name and farm.account_number:
            bank_code = self._get_bank_code(farm.bank_name)
            return (bank_code, farm.account_number)
        
        # No valid payment method
        raise ValueError(
            f"Farm {farm.farm_name} has no valid payment method. "
            "Please provide either mobile money details or bank account details."
        )
    
    def _get_mobile_money_bank_code(self, provider: str) -> str:
        """
        Map mobile money provider to Paystack bank code.
        
        Paystack uses specific codes for mobile money providers in Ghana.
        """
        mobile_money_codes = {
            'MTN Mobile Money': 'mtn-gh',
            'Vodafone Cash': 'vod-gh',
            'AirtelTigo Money': 'tgo-gh',
            'Telecel Cash': 'telecel-gh',
        }
        
        code = mobile_money_codes.get(provider)
        if not code:
            raise ValueError(f"Unknown mobile money provider: {provider}")
        
        return code
    
    def _get_bank_code(self, bank_name: str) -> str:
        """
        Map bank name to Paystack bank code.
        
        For Ghana banks. You'll need to expand this list based on
        available banks in Ghana.
        """
        # Common Ghana banks
        bank_codes = {
            'GCB Bank': 'gcb-gh',
            'Ecobank Ghana': 'ecobank-gh',
            'Stanbic Bank': 'stanbic-gh',
            'Zenith Bank': 'zenith-gh',
            'Fidelity Bank': 'fidelity-gh',
            'Absa Bank Ghana': 'absa-gh',
            'Standard Chartered': 'sc-gh',
            'Guaranty Trust Bank': 'gtb-gh',
            'CalBank': 'cal-gh',
            'Access Bank Ghana': 'access-gh',
        }
        
        # Try exact match first
        code = bank_codes.get(bank_name)
        
        # Try partial match (case-insensitive)
        if not code:
            bank_name_lower = bank_name.lower()
            for name, code in bank_codes.items():
                if name.lower() in bank_name_lower or bank_name_lower in name.lower():
                    return code
        
        # If still not found, raise error
        if not code:
            raise ValueError(
                f"Unknown bank: {bank_name}. "
                f"Supported banks: {', '.join(bank_codes.keys())}"
            )
        
        return code
    
    def get_subaccount(self, subaccount_code: str) -> Dict:
        """
        Fetch subaccount details from Paystack.
        
        Args:
            subaccount_code: Paystack subaccount code
            
        Returns:
            Dict containing subaccount details
        """
        try:
            response = self.paystack.get(f'/subaccount/{subaccount_code}')
            return response.get('data', {})
        except PaystackAPIError as e:
            logger.error(f"Failed to fetch subaccount {subaccount_code}: {e.message}")
            raise
    
    def update_subaccount(self, farm: Farm, **kwargs) -> Dict:
        """
        Update subaccount details.
        
        Args:
            farm: Farm instance with existing subaccount
            **kwargs: Fields to update (business_name, settlement_bank, account_number, etc.)
            
        Returns:
            Updated subaccount details
        """
        if not farm.paystack_subaccount_code:
            raise ValueError(f"Farm {farm.farm_name} has no subaccount to update")
        
        try:
            endpoint = f'/subaccount/{farm.paystack_subaccount_code}'
            response = self.paystack.put(endpoint, kwargs)
            
            logger.info(f"Subaccount {farm.paystack_subaccount_code} updated successfully")
            return response.get('data', {})
            
        except PaystackAPIError as e:
            logger.error(f"Failed to update subaccount {farm.paystack_subaccount_code}: {e.message}")
            raise
    
    def list_subaccounts(self, page: int = 1, per_page: int = 50) -> Dict:
        """
        List all subaccounts.
        
        Args:
            page: Page number
            per_page: Results per page
            
        Returns:
            Dict containing list of subaccounts
        """
        try:
            params = {'page': page, 'perPage': per_page}
            response = self.paystack.get('/subaccount', params=params)
            return response.get('data', [])
        except PaystackAPIError as e:
            logger.error(f"Failed to list subaccounts: {e.message}")
            raise
    
    @transaction.atomic
    def deactivate_subaccount(self, farm: Farm) -> None:
        """
        Deactivate subaccount (soft delete - marks as inactive).
        
        Args:
            farm: Farm instance
        """
        farm.subaccount_active = False
        farm.save(update_fields=['subaccount_active', 'updated_at'])
        logger.info(f"Subaccount {farm.paystack_subaccount_code} deactivated")
    
    @transaction.atomic
    def reactivate_subaccount(self, farm: Farm) -> None:
        """
        Reactivate previously deactivated subaccount.
        
        Args:
            farm: Farm instance
        """
        if not farm.paystack_subaccount_code:
            raise ValueError(f"Farm {farm.farm_name} has no subaccount")
        
        farm.subaccount_active = True
        farm.save(update_fields=['subaccount_active', 'updated_at'])
        logger.info(f"Subaccount {farm.paystack_subaccount_code} reactivated")
    
    def ensure_subaccount_exists(self, farm: Farm) -> str:
        """
        Ensure farm has an active subaccount, create if missing.
        
        Args:
            farm: Farm instance
            
        Returns:
            Subaccount code
        """
        if farm.paystack_subaccount_code and farm.subaccount_active:
            return farm.paystack_subaccount_code
        
        # Create subaccount if missing
        subaccount_data = self.create_subaccount(farm)
        return subaccount_data['subaccount_code']
