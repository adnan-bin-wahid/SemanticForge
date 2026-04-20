"""
Database service for user management.
Handles CRUD operations and data persistence.
"""

from typing import List, Optional
from .user import User


class UserDatabase:
    """In-memory user database with basic CRUD operations."""
    
    def __init__(self):
        self.users: dict[str, User] = {}
        self._id_counter = 1
    
    def create_user(self, name: str, email: str) -> User:
        """Create and store a new user."""
        user = User(name=name, email=email)
        self.users[str(self._id_counter)] = user
        self._id_counter += 1
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Retrieve a user by ID."""
        return self.users.get(user_id)
    
    def get_all_users(self) -> List[User]:
        """Get all users in the database."""
        return list(self.users.values())
    
    def update_user(self, user_id: str, name: str = None, email: str = None) -> Optional[User]:
        """Update user information."""
        user = self.users.get(user_id)
        if user:
            if name:
                user.name = name
            if email:
                user.email = email
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user by ID."""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False
    
    def count_users(self) -> int:
        """Count total users in database."""
        return len(self.users)
