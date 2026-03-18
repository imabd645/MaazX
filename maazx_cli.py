import os
import sys
import datetime
import traceback

# Add the current directory to path if needed for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import config

# 1. Validate environment
config.validate()

# 2. Import tools so they auto-register via @register_tool
import tools

# 3. Import Agent
from core.agent import Agent

# ANSI Colors
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BLUE = "\033[94m"

def print_header():
    print(f"\n{BOLD}{CYAN}==================================================={RESET}")
    print(f"{BOLD}{MAGENTA}        MaazX - Autonomous Engineering Partner      {RESET}")
    print(f"{BOLD}{CYAN}==================================================={RESET}")
    print(f"{YELLOW}Type 'exit' or 'quit' to close. Type '/clear' to clear console.{RESET}\n")

import database

def get_prompt():
    settings = database.load_settings()
    cwd = settings.get("cwd", os.getcwd())
    
    basename = os.path.basename(cwd)
    if not basename:
        basename = cwd
    return f"{BOLD}{GREEN}maazx@terminal{RESET}:{BLUE}~/{basename}{RESET}$ "

def main():
    # Enable ANSI escape sequences on Windows
    if os.name == 'nt':
        os.system('color')
        
    print_header()
    
    # Initialize the agent
    print(f"{CYAN}Initializing MaazX Core Engine...{RESET}", end="", flush=True)
    try:
        agent = Agent()
        print(f"\r{CYAN}Initializing MaazX Core Engine... {GREEN}[OK]{RESET}\n")
    except Exception as e:
        print(f"\r{RED}Failed to initialize Core Engine: {e}{RESET}\n")
        traceback.print_exc()
        return

    while True:
        try:
            prompt = get_prompt()
            user_input = input(prompt)
            
            if not user_input.strip():
                continue
                
            cmd = user_input.strip().lower()
            
            if cmd in ['exit', 'quit']:
                print(f"\n{MAGENTA}Session terminated. Goodbye!{RESET}")
                break
            elif cmd == '/clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                print_header()
                continue
            elif cmd == 'whoami':
                print(f"{CYAN}MaazX - Autonomous Engineering Partner{RESET}")
                continue
            elif cmd == 'creator':
                print(f"{CYAN}Abdullah Masood (UET Lahore){RESET}")
                continue
            elif cmd == 'purpose':
                print(f"{CYAN}Bridge AI intelligence with real-world engineering{RESET}")
                continue
            elif cmd == 'status':
                print(f"{GREEN}● Ready to collaborate{RESET}")
                continue
                
            # Send to Agent
            print(f"{MAGENTA}MaazX is thinking...{RESET}")
            reply = agent.send(user_input)
            
            # Print Agent Reply
            print(f"\n{BOLD}{CYAN}MaazX:{RESET}")
            print(f"{reply}\n")
            
        except (KeyboardInterrupt, EOFError):
            print(f"\n{MAGENTA}Session terminated. Goodbye!{RESET}")
            break
        except Exception as e:
            print(f"\n{RED}An error occurred: {e}{RESET}")
            traceback.print_exc()

if __name__ == "__main__":
    main()
