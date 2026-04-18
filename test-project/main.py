from .models.user import User
from .utils.helpers import format_greeting

def main():
    user = User(name="Alice", email="alice@example.com")
    greeting = format_greeting(user.name)
    print(greeting)

if __name__ == "__main__":
    main()
