"""
Calculator Logic Module
Handles all mathematical operations and scientific functions.
"""

import math


class CalculatorLogic:
    """Handles mathematical calculations for the calculator."""
    
    def __init__(self):
        """Initialize the calculator logic."""
        self.operations = {
            '+': self.add,
            '-': self.subtract,
            '*': self.multiply,
            '/': self.divide,
            '^': self.power,
            '%': self.percentage,
        }
        
        self.functions = {
            'sin': self.sin,
            'cos': self.cos,
            'tan': self.tan,
            'asin': self.asin,
            'acos': self.acos,
            'atan': self.atan,
            'log': self.log,
            'ln': self.ln,
            'exp': self.exp,
            'sqrt': self.sqrt,
            'sqr': self.square,
            'cube': self.cube,
            'fact': self.factorial,
            'abs': self.absolute,
            'inv': self.inverse,
            '10^x': self.power_of_10,
            'e^x': self.power_of_e,
            'sinh': self.sinh,
            'cosh': self.cosh,
            'tanh': self.tanh,
        }
    
    # Basic arithmetic operations
    def add(self, a, b):
        """Add two numbers."""
        return a + b
    
    def subtract(self, a, b):
        """Subtract b from a."""
        return a - b
    
    def multiply(self, a, b):
        """Multiply two numbers."""
        return a * b
    
    def divide(self, a, b):
        """Divide a by b."""
        if b == 0:
            return "Error: Division by zero"
        return a / b
    
    def power(self, a, b):
        """Raise a to the power of b."""
        try:
            return a ** b
        except (OverflowError, ValueError):
            return "Error"
    
    def percentage(self, a, b):
        """Calculate percentage: a % of b."""
        return (a * b) / 100
    
    # Scientific functions (input in degrees for trig functions)
    def sin(self, x):
        """Calculate sine of x (x in degrees)."""
        return math.sin(math.radians(x))
    
    def cos(self, x):
        """Calculate cosine of x (x in degrees)."""
        return math.cos(math.radians(x))
    
    def tan(self, x):
        """Calculate tangent of x (x in degrees)."""
        try:
            return math.tan(math.radians(x))
        except ValueError:
            return "Error"
    
    def asin(self, x):
        """Calculate arcsine of x (result in degrees)."""
        if -1 <= x <= 1:
            return math.degrees(math.asin(x))
        return "Error"
    
    def acos(self, x):
        """Calculate arccosine of x (result in degrees)."""
        if -1 <= x <= 1:
            return math.degrees(math.acos(x))
        return "Error"
    
    def atan(self, x):
        """Calculate arctangent of x (result in degrees)."""
        return math.degrees(math.atan(x))
    
    def log(self, x):
        """Calculate base-10 logarithm of x."""
        if x > 0:
            return math.log10(x)
        return "Error"
    
    def ln(self, x):
        """Calculate natural logarithm of x."""
        if x > 0:
            return math.log(x)
        return "Error"
    
    def exp(self, x):
        """Calculate e raised to the power of x."""
        try:
            return math.exp(x)
        except OverflowError:
            return "Error"
    
    def sqrt(self, x):
        """Calculate square root of x."""
        if x >= 0:
            return math.sqrt(x)
        return "Error"
    
    def square(self, x):
        """Calculate square of x."""
        return x * x
    
    def cube(self, x):
        """Calculate cube of x."""
        return x * x * x
    
    def factorial(self, x):
        """Calculate factorial of x (x must be non-negative integer)."""
        try:
            if x < 0 or x != int(x):
                return "Error"
            return math.factorial(int(x))
        except (ValueError, OverflowError):
            return "Error"
    
    def absolute(self, x):
        """Calculate absolute value of x."""
        return abs(x)
    
    def inverse(self, x):
        """Calculate reciprocal of x."""
        if x != 0:
            return 1 / x
        return "Error"
    
    def power_of_10(self, x):
        """Calculate 10 raised to the power of x."""
        try:
            return 10 ** x
        except OverflowError:
            return "Error"
    
    def power_of_e(self, x):
        """Calculate e raised to the power of x."""
        try:
            return math.exp(x)
        except OverflowError:
            return "Error"
    
    def sinh(self, x):
        """Calculate hyperbolic sine of x."""
        return math.sinh(x)
    
    def cosh(self, x):
        """Calculate hyperbolic cosine of x."""
        return math.cosh(x)
    
    def tanh(self, x):
        """Calculate hyperbolic tangent of x."""
        return math.tanh(x)
    
    # Helper methods
    def calculate_operation(self, operator, a, b):
        """Calculate the result of a binary operation."""
        if operator in self.operations:
            result = self.operations[operator](a, b)
            if isinstance(result, str) and result.startswith("Error"):
                return "Error"
            return result
        return "Error"
    
    def calculate_function(self, func_name, x):
        """Calculate the result of a unary function."""
        if func_name in self.functions:
            result = self.functions[func_name](x)
            if isinstance(result, str) and result.startswith("Error"):
                return "Error"
            return result
        return "Error"
    
    def get_available_operations(self):
        """Get list of available operations."""
        return list(self.operations.keys())
    
    def get_available_functions(self):
        """Get list of available functions."""
        return list(self.functions.keys())


# Test the logic module
if __name__ == "__main__":
    logic = CalculatorLogic()
    
    # Test basic operations
    print("Testing basic operations:")
    print(f"2 + 3 = {logic.add(2, 3)}")
    print(f"5 - 2 = {logic.subtract(5, 2)}")
    print(f"4 * 3 = {logic.multiply(4, 3)}")
    print(f"10 / 2 = {logic.divide(10, 2)}")
    
    # Test scientific functions
    print("\nTesting scientific functions:")
    print(f"sin(30) = {logic.sin(30):.4f}")
    print(f"cos(60) = {logic.cos(60):.4f}")
    print(f"log(100) = {logic.log(100)}")
    print(f"sqrt(25) = {logic.sqrt(25)}")
    
    print("\nCalculator logic module is working correctly!")