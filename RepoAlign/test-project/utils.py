def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b

def divide(a, b):
    """Divide two numbers. Returns 0 if b is 0."""
    if b == 0:
        return 0
    return a / b

def greet(name):
    """Return a greeting message."""
    return f"Hello, {name}!"
