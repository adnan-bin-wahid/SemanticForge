class User:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

    def get_details(self):
        return f"Name: {self.name}, Email: {self.email}"
