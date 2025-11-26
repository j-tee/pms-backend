"""
Paystack Service - Base API integration

Handles all Paystack API calls with authentication, error handling, and logging.
"""

import requests
import logging
from typing import Dict, Optional, Any
from django.conf import settings


logger = logging.getLogger(__name__)


class PaystackService:
    """
    Base service for Paystack API integration.
    
    Provides authenticated API calls to Paystack with:
    - Automatic header configuration
    - Error handling and logging
    - Response parsing
    """
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = settings.PAYSTACK_BASE_URL
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Paystack API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/transaction/initialize')
            data: Request body data
            params: URL query parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            PaystackAPIError: If API call fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.info(f"Paystack API {method} {endpoint}")
            
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30
            )
            
            response_data = response.json()
            
            # Paystack always returns status in response
            if response.status_code >= 400 or not response_data.get('status'):
                error_message = response_data.get('message', 'Unknown error')
                logger.error(f"Paystack API error: {error_message}")
                raise PaystackAPIError(error_message, response.status_code, response_data)
            
            logger.info(f"Paystack API success: {response_data.get('message')}")
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API request failed: {str(e)}")
            raise PaystackAPIError(f"Request failed: {str(e)}")
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET request to Paystack API"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict) -> Dict:
        """POST request to Paystack API"""
        return self._make_request('POST', endpoint, data=data)
    
    def put(self, endpoint: str, data: Dict) -> Dict:
        """PUT request to Paystack API"""
        return self._make_request('PUT', endpoint, data=data)
    
    def delete(self, endpoint: str) -> Dict:
        """DELETE request to Paystack API"""
        return self._make_request('DELETE', endpoint)


class PaystackAPIError(Exception):
    """
    Exception raised for Paystack API errors.
    
    Attributes:
        message: Error message from Paystack
        status_code: HTTP status code
        response_data: Full response from Paystack
    """
    
    def __init__(self, message: str, status_code: int = None, response_data: Dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)
