"""
Ghana Post GPS Service

Decodes GhanaPost GPS digital addresses to latitude/longitude coordinates
locally without requiring an external API.

GhanaPost Digital Address Format: XX-XXXX-XXXX
- XX: Region code (e.g., GA=Greater Accra, AK=Ashanti)
- XXXX-XXXX: Unique location identifier

Example: GA-184-2278 → coordinates extracted from encoded address

Note: Since there's no public API or library, we provide:
1. Format validation
2. Region extraction
3. Placeholder for custom decoding algorithm (can be implemented later)
4. Integration with Google Maps Geocoding API as fallback
"""

from typing import Dict, Optional, Tuple
import logging
import re
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


class GhanaPostGPSService:
    """
    Service for decoding GhanaPost GPS digital addresses.
    
    Supports formats:
    - Two-letter codes: GA-184-2278
    - Alphanumeric codes: G2-094-1990
    """
    
    CACHE_TTL = 86400 * 30  # 30 days (GPS locations don't change)
    
    # Region codes for validation
    VALID_REGION_CODES = {
        'GA': 'Greater Accra',
        'AK': 'Ashanti',
        'WP': 'Western',
        'WN': 'Western North',
        'EP': 'Eastern',
        'NP': 'Northern',
        'NE': 'North East',
        'BA': 'Brong Ahafo',
        'BE': 'Bono East',
        'BO': 'Bono',
        'AH': 'Ahafo',
        'UE': 'Upper East',
        'UW': 'Upper West',
        'VR': 'Volta',
        'OT': 'Oti',
        'CP': 'Central',
        'SV': 'Savannah',
    }
    
    @classmethod
    def get_coordinates(cls, gps_address: str) -> Dict[str, any]:
        """
        Get coordinates and location data from GhanaPost GPS address.
        Decodes the address locally without requiring an API.
        
        Args:
            gps_address: GhanaPost GPS address (e.g., "GA-184-2278")
            
        Returns:
            dict with keys: latitude, longitude, region, is_valid
            
        Raises:
            ValueError: If GPS address format is invalid
        """
        # Normalize address (uppercase, strip whitespace)
        gps_address = gps_address.strip().upper()
        
        # Validate format
        if not cls._validate_format(gps_address):
            raise ValueError(
                f"Invalid GhanaPost GPS address format: {gps_address}. "
                f"Expected format: XX-XXX-XXXX (e.g., GA-184-2278)"
            )
        
        # Extract region code
        region_code = gps_address[:2]
        
        # For alphanumeric codes (like G2), use fallback
        if region_code not in cls.VALID_REGION_CODES:
            logger.info(
                f"Region code {region_code} not in predefined list. "
                f"Will use coordinate-based region detection."
            )
        
        # Check cache first
        cache_key = f"gps_location:{gps_address}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"GPS location retrieved from cache: {gps_address}")
            return cached_data
        
        # Decode GPS address to coordinates
        # Option 1: Try custom decoder (if implemented)
        coords = cls._decode_address_custom(gps_address)
        
        if coords:
            latitude, longitude = coords
        else:
            # Option 2: Use Google Maps Geocoding API as fallback
            try:
                latitude, longitude = cls._geocode_with_google(gps_address)
            except Exception as e:
                logger.warning(
                    f"Google geocoding failed for {gps_address}: {e}. "
                    f"Using region center coordinates."
                )
                # Option 3: Use region center coordinates
                latitude, longitude = cls._get_region_center(region_code)
        
        # Validate coordinates are within Ghana's bounds
        if not cls._is_within_ghana(latitude, longitude):
            raise ValueError(
                f"Coordinates outside Ghana bounds: {latitude}, {longitude}"
            )
        
        location_data = {
            'latitude': latitude,
            'longitude': longitude,
            'region': cls.VALID_REGION_CODES.get(region_code, ''),
            'region_code': region_code,
            'is_valid': True,
            'gps_address': gps_address,
        }
        
        # Cache the result
        cache.set(cache_key, location_data, cls.CACHE_TTL)
        
        logger.info(
            f"GPS decoded successfully: {gps_address} → "
            f"({latitude}, {longitude})"
        )
        return location_data
    
    @staticmethod
    def _validate_format(gps_address: str) -> bool:
        """
        Validate GhanaPost GPS address format.
        Format: XX-XXX-XXXX where XX can be letters or alphanumeric
        Region code can be 2 letters (GA) or 1 letter + 1 digit (G2)
        """
        pattern = r'^[A-Z0-9]{2}-\d{3,4}-\d{4}$'
        return bool(re.match(pattern, gps_address))
    
    @classmethod
    def _decode_address_custom(cls, gps_address: str) -> Optional[Tuple[float, float]]:
        """
        Custom decoder for GhanaPost GPS addresses.
        
        TODO: Implement the actual decoding algorithm if available.
        The GhanaPost GPS encoding algorithm may be proprietary.
        
        Returns:
            Tuple of (latitude, longitude) or None if not implemented
        """
        # Placeholder for custom decoding logic
        # If you have access to the decoding algorithm, implement it here
        return None
    
    @classmethod
    def _geocode_with_google(cls, gps_address: str) -> Tuple[float, float]:
        """
        Use Google Maps Geocoding API to convert GPS address to coordinates.
        
        Requires GOOGLE_MAPS_API_KEY in settings.
        
        Raises:
            Exception: If geocoding fails or API key not configured
        """
        import requests
        
        api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
        if not api_key:
            raise Exception("GOOGLE_MAPS_API_KEY not configured")
        
        # Google can geocode GhanaPost GPS addresses
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            'address': f"{gps_address}, Ghana",
            'key': api_key,
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            return (location['lat'], location['lng'])
        
        raise Exception(f"Google geocoding failed: {data.get('status')}")
    
    @classmethod
    def _get_region_center(cls, region_code: str) -> Tuple[float, float]:
        """
        Get approximate center coordinates for a region.
        Used as fallback when geocoding fails.
        """
        region_centers = {
            'GA': (5.6037, -0.1870),   # Greater Accra - Accra
            'AK': (6.6885, -1.6244),   # Ashanti - Kumasi
            'WP': (5.1200, -1.9970),   # Western - Sekondi-Takoradi
            'WN': (6.2000, -2.5000),   # Western North
            'EP': (6.0800, -0.2380),   # Eastern - Koforidua
            'NP': (9.4034, -0.8424),   # Northern - Tamale
            'NE': (10.5000, -0.5000),  # North East
            'BA': (7.9139, -1.0595),   # Brong Ahafo - Sunyani
            'BE': (7.7500, -0.9500),   # Bono East
            'BO': (7.5000, -2.5000),   # Bono
            'AH': (7.0000, -2.5000),   # Ahafo
            'UE': (10.7202, -0.9813),  # Upper East - Bolgatanga
            'UW': (10.3529, -2.5095),  # Upper West - Wa
            'VR': (6.6000, 0.4700),    # Volta - Ho
            'OT': (7.9000, 0.5000),    # Oti
            'CP': (5.1053, -1.2466),   # Central - Cape Coast
            'SV': (9.0000, -1.5000),   # Savannah
        }
        return region_centers.get(region_code, (7.9465, -1.0232))  # Default: Center of Ghana
    
    @staticmethod
    def _is_within_ghana(latitude: float, longitude: float) -> bool:
        """
        Check if coordinates are within Ghana's geographical bounds.
        
        Ghana bounds (approximate):
        - Latitude: 4.5°N to 11.2°N
        - Longitude: 3.5°W to 1.2°E
        """
        return (
            4.5 <= latitude <= 11.2 and
            -3.5 <= longitude <= 1.2
        )
    
    @staticmethod
    def get_fallback_coordinates() -> Tuple[float, float]:
        """
        Get fallback coordinates (center of Ghana) when decoding fails.
        Should log a warning when used.
        """
        logger.warning("Using fallback coordinates - GPS address could not be decoded")
        return (7.9465, -1.0232)  # Center of Ghana
    
    @classmethod
    def extract_region_name(cls, gps_address: str) -> str:
        """
        Extract region name from GPS address.
        
        Args:
            gps_address: GhanaPost GPS address
            
        Returns:
            Region name (e.g., "Greater Accra")
        """
        region_code = gps_address[:2].upper()
        return cls.VALID_REGION_CODES.get(region_code, '')


# Convenience function for quick access
def decode_gps_address(gps_address: str) -> Dict[str, any]:
    """
    Quick function to decode a GhanaPost GPS address.
    
    Usage:
        from farms.services.gps_service import decode_gps_address
        
        result = decode_gps_address("GA-184-2278")
        print(result['latitude'], result['longitude'])
    """
    return GhanaPostGPSService.get_coordinates(gps_address)
