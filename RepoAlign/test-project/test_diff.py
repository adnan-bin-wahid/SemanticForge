def add(a, b, c=0):
    """Add up to three numbers"""
    return a + b + c

def multiply(a, b):
    """Multiply two numbers"""
    return a * b

class AdvancedCalc:
    """Advanced calculator with methods"""
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
