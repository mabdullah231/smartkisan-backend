"""
Phone number validation for Pakistani mobile numbers.
Format: 03XXXXXXXXX (11 digits, starting with 03)
"""
import re
from typing import Optional
from pydantic import field_validator

# Pakistani mobile number pattern: 03XXXXXXXXX (11 digits)
PAKISTANI_PHONE_PATTERN = re.compile(r'^03\d{9}$')

def validate_pakistani_phone(phone: str) -> str:
    """
    Validates and normalizes Pakistani phone number.
    
    Args:
        phone: Phone number string
        
    Returns:
        Normalized phone number string (03XXXXXXXXX)
        
    Raises:
        ValueError: If phone number is invalid
    """
    if not phone:
        raise ValueError("Phone number is required")
    
    # Remove any whitespace
    phone = phone.strip()
    
    # Remove any dashes, spaces, or other separators
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Check if it starts with +92, convert to 0 format
    if phone.startswith('+92'):
        phone = '0' + phone[3:]
    elif phone.startswith('92'):
        phone = '0' + phone[2:]
    
    # Validate format: must be 03XXXXXXXXX (11 digits starting with 03)
    if not PAKISTANI_PHONE_PATTERN.match(phone):
        raise ValueError(
            "Invalid phone number format. Phone number must be in format: 03XXXXXXXXX "
            "(11 digits starting with 03, e.g., 03001234567)"
        )
    
    return phone

def phone_validator():
    """Returns a Pydantic field validator for phone numbers"""
    @field_validator('phone', mode='before')
    @classmethod
    def validate_phone(cls, v):
        if v is None:
            return v
        return validate_pakistani_phone(str(v))
    
    return validate_phone

