#!/usr/bin/env python3
"""
Scientific Calculator with GUI
A comprehensive scientific calculator with modern UI using CustomTkinter.
"""

import customtkinter as ctk
import math
import json
import os
from datetime import datetime
from calculator_logic import CalculatorLogic
from calculator_history import CalculatorHistory
from calculator_gui import CalculatorGUI


class ScientificCalculator:
    """Main calculator application controller."""
    
    def __init__(self):
        """Initialize the calculator application."""
        # Set appearance mode
        ctk.set_appearance_mode("dark")  # "dark", "light", or "system"
        ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
        
        # Initialize components
        self.logic = CalculatorLogic()
        self.history = CalculatorHistory()
        self.memory = 0.0
        self.current_input = ""
        self.previous_result = ""
        self.last_operation = ""
        self.waiting_for_operand = False
        self.decimal_entered = False
        
        # Create GUI
        self.gui = CalculatorGUI(self)
        
        # Bind keyboard events
        self.bind_keyboard_events()
        
    def bind_keyboard_events(self):
        """Bind keyboard events to calculator functions."""
        self.gui.window.bind('<Key>', self.on_key_press)
        self.gui.window.bind('<Return>', lambda e: self.calculate_result())
        self.gui.window.bind('<Escape>', lambda e: self.clear_all())
        self.gui.window.bind('<BackSpace>', lambda e: self.backspace())
        self.gui.window.bind('<Delete>', lambda e: self.clear_entry())
        
    def on_key_press(self, event):
        """Handle keyboard input."""
        key = event.char
        
        if key.isdigit():
            self.input_digit(key)
        elif key == '.':
            self.input_decimal()
        elif key in '+-*/':
            self.input_operator(key)
        elif key == '=' or key == '\r':
            self.calculate_result()
        elif key == 'c' or key == 'C':
            self.clear_all()
        elif key == 'e' or key == 'E':
            self.input_constant('e')
        elif key == 'p' or key == 'P':
            self.input_constant('pi')
        elif key == '(':
            self.input_parenthesis('(')
        elif key == ')':
            self.input_parenthesis(')')
            
    def update_display(self, value=None):
        """Update the calculator display."""
        if value is not None:
            self.gui.update_display(value)
        else:
            self.gui.update_display(self.current_input or "0")
    
    def input_digit(self, digit):
        """Handle digit input."""
        if self.waiting_for_operand:
            self.current_input = ""
            self.waiting_for_operand = False
            self.decimal_entered = False
            
        if digit == '0' and self.current_input == '0':
            return
            
        if self.current_input == '0':
            self.current_input = digit
        else:
            self.current_input += digit
            
        self.update_display()
    
    def input_decimal(self):
        """Handle decimal point input."""
        if self.waiting_for_operand:
            self.current_input = "0"
            self.waiting_for_operand = False
            self.decimal_entered = False
            
        if not self.decimal_entered:
            if not self.current_input:
                self.current_input = "0"
            self.current_input += "."
            self.decimal_entered = True
            self.update_display()
    
    def input_operator(self, operator):
        """Handle operator input."""
        if self.current_input:
            if self.last_operation and not self.waiting_for_operand:
                # Perform the pending operation
                self.calculate_result()
            
            self.previous_result = self.current_input
            self.last_operation = operator
            self.waiting_for_operand = True
            self.decimal_entered = False
            
            # Update operator display
            self.gui.update_operator_display(operator)
    
    def input_function(self, func_name):
        """Handle scientific function input."""
        if not self.current_input:
            return
            
        try:
            value = float(self.current_input)
            result = self.logic.calculate_function(func_name, value)
            
            if result == "Error":
                self.current_input = "Error"
            else:
                # Add to history
                expression = f"{func_name}({self.current_input})"
                self.history.add_entry(expression, result)
                self.gui.update_history_display(self.history.get_recent(10))
                
                self.current_input = str(result)
                self.waiting_for_operand = True
                
            self.update_display()
            
        except (ValueError, TypeError):
            self.current_input = "Error"
            self.update_display()
    
    def input_constant(self, constant):
        """Handle constant input (pi, e)."""
        if constant == 'pi':
            self.current_input = str(math.pi)
        elif constant == 'e':
            self.current_input = str(math.e)
            
        self.update_display()
    
    def input_parenthesis(self, parenthesis):
        """Handle parenthesis input."""
        # For simplicity, we'll just add to current input
        self.current_input += parenthesis
        self.update_display()
    
    def calculate_result(self):
        """Calculate the result of the current operation."""
        if not self.last_operation or not self.previous_result or not self.current_input:
            return
            
        try:
            a = float(self.previous_result)
            b = float(self.current_input)
            
            result = self.logic.calculate_operation(self.last_operation, a, b)
            
            if result == "Error":
                self.current_input = "Error"
            else:
                # Add to history
                expression = f"{self.previous_result} {self.last_operation} {self.current_input}"
                self.history.add_entry(expression, result)
                self.gui.update_history_display(self.history.get_recent(10))
                
                self.current_input = str(result)
                self.last_operation = ""
                self.waiting_for_operand = True
                
            self.update_display()
            
        except (ValueError, TypeError):
            self.current_input = "Error"
            self.update_display()
    
    def clear_entry(self):
        """Clear the current entry."""
        self.current_input = ""
        self.decimal_entered = False
        self.update_display("0")
    
    def clear_all(self):
        """Clear all calculator state."""
        self.current_input = ""
        self.previous_result = ""
        self.last_operation = ""
        self.waiting_for_operand = False
        self.decimal_entered = False
        self.gui.update_operator_display("")
        self.update_display("0")
    
    def backspace(self):
        """Remove the last character from current input."""
        if self.current_input:
            if self.current_input[-1] == '.':
                self.decimal_entered = False
            self.current_input = self.current_input[:-1]
            self.update_display()
    
    def memory_store(self):
        """Store current value in memory."""
        if self.current_input and self.current_input != "Error":
            try:
                self.memory = float(self.current_input)
                self.gui.update_memory_indicator(True)
            except (ValueError, TypeError):
                pass
    
    def memory_recall(self):
        """Recall value from memory."""
        self.current_input = str(self.memory)
        self.update_display()
    
    def memory_clear(self):
        """Clear memory."""
        self.memory = 0.0
        self.gui.update_memory_indicator(False)
    
    def memory_add(self):
        """Add current value to memory."""
        if self.current_input and self.current_input != "Error":
            try:
                self.memory += float(self.current_input)
                self.gui.update_memory_indicator(True)
            except (ValueError, TypeError):
                pass
    
    def memory_subtract(self):
        """Subtract current value from memory."""
        if self.current_input and self.current_input != "Error":
            try:
                self.memory -= float(self.current_input)
                self.gui.update_memory_indicator(True)
            except (ValueError, TypeError):
                pass
    
    def toggle_sign(self):
        """Toggle the sign of the current input."""
        if self.current_input and self.current_input != "Error":
            if self.current_input[0] == '-':
                self.current_input = self.current_input[1:]
            else:
                self.current_input = '-' + self.current_input
            self.update_display()
    
    def calculate_percentage(self):
        """Calculate percentage."""
        if self.current_input and self.current_input != "Error":
            try:
                value = float(self.current_input)
                result = value / 100
                self.current_input = str(result)
                self.update_display()
            except (ValueError, TypeError):
                self.current_input = "Error"
                self.update_display()
    
    def run(self):
        """Run the calculator application."""
        self.gui.window.mainloop()


def main():
    """Main entry point for the calculator."""
    calculator = ScientificCalculator()
    calculator.run()


if __name__ == "__main__":
    main()