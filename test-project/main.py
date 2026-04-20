"""
Main entry point for the test application.
Demonstrates user and helper functionality.
"""

from models.user import User
from models.database import UserDatabase
from utils.helpers import format_greeting, validate_email, sanitize_input, format_user_info


def main():
    """Main function to demonstrate the application."""
    
    # Create database
    db = UserDatabase()
    
    # Create and add users
    user1 = User(name="Alice", email="alice@example.com")
    user2 = User(name="Bob Smith", email="bob.smith@company.org")
    user3 = User(name="Charlie Brown", email="charlie@test.net")
    
    db.create_user("Alice", "alice@example.com")
    db.create_user("Bob Smith", "bob.smith@company.org")
    db.create_user("Charlie Brown", "charlie@test.net")
    
    # Display greetings
    print(format_greeting(user1.name))
    print(format_greeting(user2.name))
    
    # Demonstrate user functionality
    print("\n--- User Details ---")
    print(user1.get_details())
    print(f"Valid email: {user1.validate_email()}")
    print(f"Username: {user1.get_username()}")
    
    # Demonstrate validation and sanitization
    print("\n--- Validation & Sanitization ---")
    test_email = "invalid.email@"
    print(f"Email '{test_email}' valid: {validate_email(test_email)}")
    
    messy_input = "Hello@#$World!"
    clean_input = sanitize_input(messy_input)
    print(f"Original: '{messy_input}' -> Cleaned: '{clean_input}'")
    
    # Display all users
    print("\n--- All Users ---")
    for user in [user1, user2, user3]:
        print(f"  {user}")


if __name__ == "__main__":
    main()
