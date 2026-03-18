"""
Calculator History Module
Manages calculation history with persistence.
"""

import json
import os
from datetime import datetime


class CalculatorHistory:
    """Manages the history of calculations."""
    
    def __init__(self, max_entries=100, history_file="calculator_history.json"):
        """
        Initialize the history manager.
        
        Args:
            max_entries: Maximum number of history entries to keep
            history_file: File to persist history to
        """
        self.max_entries = max_entries
        self.history_file = history_file
        self.history = []
        self.load_history()
    
    def add_entry(self, expression, result):
        """
        Add a new entry to the history.
        
        Args:
            expression: The mathematical expression
            result: The result of the calculation
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'expression': expression,
            'result': str(result),
            'result_value': float(result) if isinstance(result, (int, float)) else None
        }
        
        self.history.insert(0, entry)  # Add to beginning (most recent first)
        
        # Trim history if it exceeds max entries
        if len(self.history) > self.max_entries:
            self.history = self.history[:self.max_entries]
        
        # Save to file
        self.save_history()
        
        return entry
    
    def get_recent(self, count=10):
        """
        Get the most recent history entries.
        
        Args:
            count: Number of entries to return
            
        Returns:
            List of recent history entries
        """
        return self.history[:min(count, len(self.history))]
    
    def get_all(self):
        """
        Get all history entries.
        
        Returns:
            List of all history entries
        """
        return self.history
    
    def clear(self):
        """Clear all history entries."""
        self.history = []
        self.save_history()
    
    def save_history(self):
        """Save history to file."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except (IOError, OSError) as e:
            print(f"Warning: Could not save history: {e}")
    
    def load_history(self):
        """Load history from file."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.history = json.load(f)
                
                # Ensure we don't exceed max entries
                if len(self.history) > self.max_entries:
                    self.history = self.history[:self.max_entries]
                    
            except (json.JSONDecodeError, IOError, OSError) as e:
                print(f"Warning: Could not load history: {e}")
                self.history = []
        else:
            self.history = []
    
    def export_to_text(self, filename="calculator_history.txt"):
        """
        Export history to a text file.
        
        Args:
            filename: Name of the text file to export to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filename, 'w') as f:
                f.write("Calculator History\n")
                f.write("=" * 50 + "\n\n")
                
                for i, entry in enumerate(self.history, 1):
                    timestamp = datetime.fromisoformat(entry['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"{i}. {timestamp}\n")
                    f.write(f"   Expression: {entry['expression']}\n")
                    f.write(f"   Result: {entry['result']}\n")
                    f.write("-" * 40 + "\n")
            
            return True
        except (IOError, OSError) as e:
            print(f"Error exporting history: {e}")
            return False
    
    def search(self, query):
        """
        Search history for entries containing the query.
        
        Args:
            query: Search string
            
        Returns:
            List of matching history entries
        """
        query = query.lower()
        results = []
        
        for entry in self.history:
            if (query in entry['expression'].lower() or 
                query in entry['result'].lower() or
                query in entry['timestamp'].lower()):
                results.append(entry)
        
        return results
    
    def get_statistics(self):
        """
        Get statistics about the history.
        
        Returns:
            Dictionary with statistics
        """
        if not self.history:
            return {
                'total_entries': 0,
                'first_entry': None,
                'last_entry': None,
                'most_used_operators': {}
            }
        
        # Count operator usage
        operator_counts = {}
        operators = ['+', '-', '*', '/', '^', 'sin', 'cos', 'tan', 'log', 'sqrt']
        
        for entry in self.history:
            expression = entry['expression'].lower()
            for op in operators:
                if op in expression:
                    operator_counts[op] = operator_counts.get(op, 0) + 1
        
        # Sort operators by frequency
        sorted_operators = sorted(operator_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_entries': len(self.history),
            'first_entry': self.history[-1]['timestamp'] if self.history else None,
            'last_entry': self.history[0]['timestamp'] if self.history else None,
            'most_used_operators': dict(sorted_operators[:5])  # Top 5 operators
        }


# Test the history module
if __name__ == "__main__":
    history = CalculatorHistory(max_entries=5)
    
    # Add some test entries
    print("Adding test entries...")
    history.add_entry("2 + 3", 5)
    history.add_entry("sin(30)", 0.5)
    history.add_entry("10 * 5", 50)
    history.add_entry("sqrt(25)", 5)
    history.add_entry("log(100)", 2)
    history.add_entry("100 / 4", 25)  # This should push out the first entry
    
    # Get recent entries
    print("\nRecent entries:")
    for entry in history.get_recent(3):
        print(f"{entry['expression']} = {entry['result']}")
    
    # Get statistics
    stats = history.get_statistics()
    print(f"\nStatistics:")
    print(f"Total entries: {stats['total_entries']}")
    print(f"Most used operators: {stats['most_used_operators']}")
    
    # Search
    print("\nSearch for 'sin':")
    for entry in history.search('sin'):
        print(f"{entry['expression']} = {entry['result']}")
    
    print("\nHistory module is working correctly!")