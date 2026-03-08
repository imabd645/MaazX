"""
Tools package — import every tool module here so they auto-register.

To add a new tool:
  1. Create  tools/my_tool.py  with a @register_tool function
  2. Add  import tools.my_tool  below
"""

# File operations
import tools.file_read
import tools.file_create
import tools.file_edit

# Codebase scanning
import tools.list_directory
import tools.search_files
import tools.search_in_files

# Shell
import tools.run_command

# WhatsApp
import tools.send_whatsapp

# Connectivity
import tools.web_search

# Automation
import tools.schedule_action

# Data Inspection
import tools.inspect_database
