"""
Calculator GUI Module
Creates the graphical user interface for the scientific calculator.
"""

import customtkinter as ctk
from tkinter import font as tkfont


class CalculatorGUI:
    """Creates and manages the calculator GUI."""
    
    def __init__(self, controller):
        """
        Initialize the calculator GUI.
        
        Args:
            controller: The calculator controller instance
        """
        self.controller = controller
        
        # Create main window
        self.window = ctk.CTk()
        self.window.title("Scientific Calculator")
        self.window.geometry("900x700")
        self.window.resizable(True, True)
        
        # Configure grid
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        # Create main container
        self.main_container = ctk.CTkFrame(self.window)
        self.main_container.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Configure main container grid
        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)
        
        # Create left panel (calculator)
        self.left_panel = ctk.CTkFrame(self.main_container)
        self.left_panel.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Create right panel (history)
        self.right_panel = ctk.CTkFrame(self.main_container)
        self.right_panel.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Setup calculator panel
        self.setup_calculator_panel()
        
        # Setup history panel
        self.setup_history_panel()
        
        # Memory indicator
        self.memory_indicator = ctk.CTkLabel(
            self.left_panel, 
            text="",
            font=("Arial", 12, "bold"),
            text_color="green"
        )
        self.memory_indicator.grid(row=0, column=0, columnspan=6, sticky="w", padx=10)
        
        # Operator display
        self.operator_display = ctk.CTkLabel(
            self.left_panel,
            text="",
            font=("Arial", 20, "bold"),
            text_color="yellow"
        )
        self.operator_display.grid(row=1, column=4, columnspan=2, sticky="e", padx=10)
    
    def setup_calculator_panel(self):
        """Setup the calculator panel with buttons and display."""
        # Configure calculator panel grid
        for i in range(8):
            self.left_panel.grid_rowconfigure(i, weight=1)
        for i in range(6):
            self.left_panel.grid_columnconfigure(i, weight=1)
        
        # Display
        self.display = ctk.CTkEntry(
            self.left_panel,
            font=("Arial", 32, "bold"),
            justify="right",
            border_width=2,
            corner_radius=10
        )
        self.display.grid(row=1, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")
        self.display.insert(0, "0")
        
        # Create button frames
        self.create_memory_buttons()
        self.create_scientific_buttons_row1()
        self.create_scientific_buttons_row2()
        self.create_number_buttons()
        self.create_operator_buttons()
        self.create_special_buttons()
    
    def setup_history_panel(self):
        """Setup the history panel."""
        # Configure history panel grid
        self.right_panel.grid_rowconfigure(0, weight=1)
        self.right_panel.grid_rowconfigure(1, weight=0)
        self.right_panel.grid_columnconfigure(0, weight=1)
        
        # History label
        history_label = ctk.CTkLabel(
            self.right_panel,
            text="Calculation History",
            font=("Arial", 16, "bold")
        )
        history_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        # History text box
        self.history_text = ctk.CTkTextbox(
            self.right_panel,
            font=("Consolas", 12),
            wrap="word",
            state="normal"
        )
        self.history_text.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # Clear history button
        clear_history_btn = ctk.CTkButton(
            self.right_panel,
            text="Clear History",
            command=self.controller.history.clear,
            font=("Arial", 12),
            fg_color="red",
            hover_color="darkred"
        )
        clear_history_btn.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
    
    def create_memory_buttons(self):
        """Create memory function buttons."""
        # Row 2: Memory buttons
        memory_buttons = [
            ("MC", self.controller.memory_clear),
            ("MR", self.controller.memory_recall),
            ("M+", self.controller.memory_add),
            ("M-", self.controller.memory_subtract),
            ("MS", self.controller.memory_store),
        ]
        
        for i, (text, command) in enumerate(memory_buttons):
            btn = ctk.CTkButton(
                self.left_panel,
                text=text,
                command=command,
                font=("Arial", 14, "bold"),
                fg_color="gray",
                hover_color="darkgray",
                height=40
            )
            btn.grid(row=2, column=i, padx=2, pady=2, sticky="nsew")
    
    def create_scientific_buttons_row1(self):
        """Create first row of scientific buttons."""
        # Row 3: Scientific functions row 1
        sci_buttons1 = [
            ("sin", lambda: self.controller.input_function("sin")),
            ("cos", lambda: self.controller.input_function("cos")),
            ("tan", lambda: self.controller.input_function("tan")),
            ("log", lambda: self.controller.input_function("log")),
            ("ln", lambda: self.controller.input_function("ln")),
            ("e^x", lambda: self.controller.input_function("e^x")),
        ]
        
        for i, (text, command) in enumerate(sci_buttons1):
            btn = ctk.CTkButton(
                self.left_panel,
                text=text,
                command=command,
                font=("Arial", 12, "bold"),
                fg_color="#2b5797",
                hover_color="#1e3a6b",
                height=40
            )
            btn.grid(row=3, column=i, padx=2, pady=2, sticky="nsew")
    
    def create_scientific_buttons_row2(self):
        """Create second row of scientific buttons."""
        # Row 4: Scientific functions row 2
        sci_buttons2 = [
            ("asin", lambda: self.controller.input_function("asin")),
            ("acos", lambda: self.controller.input_function("acos")),
            ("atan", lambda: self.controller.input_function("atan")),
            ("10^x", lambda: self.controller.input_function("10^x")),
            ("x²", lambda: self.controller.input_function("sqr")),
            ("√x", lambda: self.controller.input_function("sqrt")),
        ]
        
        for i, (text, command) in enumerate(sci_buttons2):
            btn = ctk.CTkButton(
                self.left_panel,
                text=text,
                command=command,
                font=("Arial", 12, "bold"),
                fg_color="#2b5797",
                hover_color="#1e3a6b",
                height=40
            )
            btn.grid(row=4, column=i, padx=2, pady=2, sticky="nsew")
    
    def create_number_buttons(self):
        """Create number buttons (0-9 and decimal)."""
        # Number button layout
        number_layout = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
            ["0", ".", "±"],
        ]
        
        for row_idx, row in enumerate(number_layout):
            for col_idx, text in enumerate(row):
                actual_row = row_idx + 5  # Start at row 5
                actual_col = col_idx
                
                if text == "±":
                    command = self.controller.toggle_sign
                elif text == ".":
                    command = self.controller.input_decimal
                else:
                    command = lambda t=text: self.controller.input_digit(t)
                
                btn = ctk.CTkButton(
                    self.left_panel,
                    text=text,
                    command=command,
                    font=("Arial", 18, "bold"),
                    fg_color="#333333",
                    hover_color="#555555",
                    height=50
                )
                btn.grid(row=actual_row, column=actual_col, padx=2, pady=2, sticky="nsew")
    
    def create_operator_buttons(self):
        """Create operator buttons (+, -, *, /, =)."""
        # Operator buttons (right column)
        operators = [
            ("/", lambda: self.controller.input_operator("/")),
            ("*", lambda: self.controller.input_operator("*")),
            ("-", lambda: self.controller.input_operator("-")),
            ("+", lambda: self.controller.input_operator("+")),
            ("=", self.controller.calculate_result),
        ]
        
        for i, (text, command) in enumerate(operators):
            row = i + 5  # Start at row 5
            btn = ctk.CTkButton(
                self.left_panel,
                text=text,
                command=command,
                font=("Arial", 18, "bold"),
                fg_color="#ff9500",
                hover_color="#cc7700",
                height=50 if text != "=" else 60
            )
            btn.grid(row=row, column=4, padx=2, pady=2, sticky="nsew")
            
            # Make equals button span 2 rows
            if text == "=":
                btn.grid(row=row, column=5, rowspan=2, padx=2, pady=2, sticky="nsew")
    
    def create_special_buttons(self):
        """Create special function buttons (C, CE, %, π, e, x^y, x!, |x|, 1/x)."""
        # Special buttons column (column 5, except = which is row 8-9)
        special_buttons = [
            ("C", self.controller.clear_all),
            ("CE", self.controller.clear_entry),
            ("%", self.controller.calculate_percentage),
            ("π", lambda: self.controller.input_constant("pi")),
            ("e", lambda: self.controller.input_constant("e")),
            ("x^y", lambda: self.controller.input_operator("^")),
            ("x!", lambda: self.controller.input_function("fact")),
            ("|x|", lambda: self.controller.input_function("abs")),
            ("1/x", lambda: self.controller.input_function("inv")),
        ]
        
        for i, (text, command) in enumerate(special_buttons):
            row = i
            btn = ctk.CTkButton(
                self.left_panel,
                text=text,
                command=command,
                font=("Arial", 12, "bold"),
                fg_color="#555555",
                hover_color="#777777",
                height=40
            )
            btn.grid(row=row, column=5, padx=2, pady=2, sticky="nsew")
    
    def update_display(self, value):
        """Update the calculator display."""
        self.display.delete(0, "end")
        self.display.insert(0, str(value))
    
    def update_operator_display(self, operator):
        """Update the operator display."""
        self.operator_display.configure(text=operator)
    
    def update_memory_indicator(self, has_memory):
        """Update the memory indicator."""
        if has_memory:
            self.memory_indicator.configure(text="M")
        else:
            self.memory_indicator.configure(text="")
    
    def update_history_display(self, history_entries):
        """Update the history display."""
        self.history_text.delete("1.0", "end")
        
        if not history_entries:
            self.history_text.insert("1.0", "No history yet.")
            return
        
        for entry in history_entries:
            # Format the entry nicely
            expression = entry['expression']
            result = entry['result']
            
            # Truncate long expressions
            if len(expression) > 30:
                expression = expression[:27] + "..."
            
            line = f"{expression} = {result}\n"
            self.history_text.insert("end", line)
        
        # Scroll to bottom
        self.history_text.see("end")


# Test the GUI module
if __name__ == "__main__":
    # Create a mock controller for testing
    class MockController:
        def __init__(self):
            self.history = type('obj', (object,), {'clear': lambda: print("Clear history")})()
        
        def input_digit(self, digit):
            print(f"Input digit: {digit}")
        
        def input_operator(self, op):
            print(f"Input operator: {op}")
        
        def input_function(self, func):
            print(f"Input function: {func}")
        
        def input_decimal(self):
            print("Input decimal")
        
        def input_constant(self, const):
            print(f"Input constant: {const}")
        
        def calculate_result(self):
            print("Calculate result")
        
        def clear_all(self):
            print("Clear all")
        
        def clear_entry(self):
            print("Clear entry")
        
        def memory_clear(self):
            print("Memory clear")
        
        def memory_recall(self):
            print("Memory recall")
        
        def memory_add(self):
            print("Memory add")
        
        def memory_subtract(self):
            print("Memory subtract")
        
        def memory_store(self):
            print("Memory store")
        
        def toggle_sign(self):
            print("Toggle sign")
        
        def calculate_percentage(self):
            print("Calculate percentage")
    
    print("Testing GUI...")
    controller = MockController()
    gui = CalculatorGUI(controller)
    gui.window.mainloop()