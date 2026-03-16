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

# Shell & REPL
import tools.run_command
import tools.python_repl

# WhatsApp
import tools.send_whatsapp

# Connectivity
import tools.web_search

# Automation
import tools.schedule_action

# Data Inspection
import tools.inspect_database

# Agent Memory
import tools.whatsapp_admin
import tools.whatsapp_search
import tools.whatsapp_voice_vibe
import tools.manage_memory
import tools.query_knowledge

# Gmail Integration
import tools.gmail

# PC Control
import tools.pc_control

# System Monitor
import tools.system_monitor

# Git Manager
import tools.git_manager
import tools.github_tools

# Webcam Control
import tools.webcam

# File Porter
import tools.file_transfer

# Browser Automation
import tools.browser_automation

# Vision Intelligence
import tools.vision_intelligence

# LinkedIn Management
import tools.linkedin_manager
