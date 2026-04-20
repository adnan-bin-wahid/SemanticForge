import re
from typing import List


def format_greeting(name: str) -> str:
    """
    Formats a greeting message.
    """
    return f"Hello, {name}!"


def validate_email(email: str) -> bool:
    """
    Validates if an email address has correct format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email format is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_input(text: str) -> str:
    """
    Sanitizes input by removing special characters.
    
    Args:
        text: Text to sanitize
        
    Returns:
        str: Sanitized text with only alphanumeric and spaces
    """
    return re.sub(r'[^a-zA-Z0-9\s]', '', text)


def split_fullname(fullname: str) -> tuple[str, str]:
    """
    Splits a full name into first and last name.
    
    Args:
        fullname: Full name string
        
    Returns:
        tuple: (first_name, last_name)
    """
    parts = fullname.strip().split()
    if len(parts) >= 2:
        return parts[0], ' '.join(parts[1:])
    return fullname, ""


def format_user_info(name: str, email: str) -> str:
    """
    Formats user information in a readable way.
    
    Args:
        name: User's name
        email: User's email
        
    Returns:
        str: Formatted user information
    """
    return f"User: {name}\nEmail: {email}\nEmail Valid: {validate_email(email)}"
