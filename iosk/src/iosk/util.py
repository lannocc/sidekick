# src/iosk/util.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

"""
Centralized utility functions and constants for the IOSK system.
"""

# AI Prompt Formatting Constants
# As per the refactoring proposal, these constants centralize the markers
# used to structure the AI's context, preventing inconsistencies.

AI_MEM_HEADER = '\n=== CORE RULES/MEMORY BEGIN ===\n'
AI_MEM_PROMPT = 'THIS SECTION IS MOST IMPORTANT, I MUST ALWAYS REMEMBER:\n'
AI_MEM_FOOTER = '\n=== END   CORE RULES/MEMORY ===\n'

AI_HISTORY_HEADER = '\n=== IOSK PERSONAL CHAT HISTORY BEGIN ===\n'
AI_HISTORY_FOOTER = '\n=== END   IOSK PERSONAL CHAT HISTORY ===\n'