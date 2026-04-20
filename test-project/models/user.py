import re
from typing import Optional


class User:
    """Represents a user with name and email."""
    
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email
        self.created_at = None
        self.is_active = True

    def get_details(self) -> str:
        """Returns a string representation of user details."""
        return f"Name: {self.name}, Email: {self.email}"
    
    def validate_email(self) -> bool:
        """
        Validates the user's email address format.
        
        Returns:
            bool: True if email is valid
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, self.email) is not None
    
    def get_username(self) -> str:
        """
        Extracts username from email address.
        
        Returns:
            str: Username part before @
        """
        if '@' in self.email:
            return self.email.split('@')[0]
        return self.name.lower().replace(' ', '.')
    
    def get_domain(self) -> Optional[str]:
        """
        Extracts domain from email address.
        
        Returns:
            str: Domain part after @, or None
        """
        if '@' in self.email:
            return self.email.split('@')[1]
        return None
    
    def deactivate(self):
        """Deactivates the user account."""
        self.is_active = False
    
    def activate(self):
        """Activates the user account."""
        self.is_active = True
    
    def is_valid(self) -> bool:
        """
        Checks if user data is valid.
        
        Returns:
            bool: True if name and email are present and email is valid
        """
        return bool(self.name) and bool(self.email) and self.validate_email()
    
    def __str__(self) -> str:
        """String representation of user."""
        status = "Active" if self.is_active else "Inactive"
        return f"{self.name} ({self.email}) - {status}"
    
    def __repr__(self) -> str:
        """Developer representation of user."""
        return f"User(name='{self.name}', email='{self.email}', active={self.is_active})"
