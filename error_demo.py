#!/usr/bin/env python
"""Demo script to show Rich's error formatting capabilities."""
from rich.traceback import install

# Install rich traceback handler with all bells and whistles
install(show_locals=True, width=120, word_wrap=True, extra_lines=3, 
        theme="monokai", suppress=[])

def function_c(value):
    """This function will raise an error."""
    # Let's try to convert a string to an integer
    some_local_var = "sample variable"
    return int(value)  # This will fail if value is not a number

def function_b(value):
    """Call function_c with a value."""
    result = function_c(value)
    return result * 2

def function_a():
    """Top level function that starts the chain."""
    user_input = "not a number"
    return function_b(user_input)

if __name__ == "__main__":
    # This will generate a nice traceback
    print("Attempting to demonstrate Rich's error formatting...")
    result = function_a()
    print(f"Result: {result}")  # We'll never get here 