# src/iosk/util.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

"""
Centralized utility functions and constants for the IOSK system.
"""
import shlex
from datetime import timedelta

# 1. ANSI Color Codes
# Centralized from bin/color.py and bin/colors.py
COLOR_MAP = {
    'black': '\033[30m', 'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m',
    'blue': '\033[34m', 'magenta': '\033[35m', 'cyan': '\033[36m', 'white': '\033[37m',
    'bright_black': '\033[90m', 'bright_red': '\033[91m', 'bright_green': '\033[92m',
    'bright_yellow': '\033[93m', 'bright_blue': '\033[94m', 'bright_magenta': '\033[95m',
    'bright_cyan': '\033[96m', 'bright_white': '\033[97m',
}
REVERSE_COLOR_MAP = {v: k for k, v in COLOR_MAP.items()}
RESET_CODE = '\033[0m'

# AI Prompt Formatting Constants
# As per the refactoring proposal, these constants centralize the markers
# used to structure the AI's context, preventing inconsistencies.

AI_MEM_HEADER = '\n=== CORE RULES/MEMORY BEGIN ===\n'
AI_MEM_PROMPT = 'THIS SECTION IS MOST IMPORTANT, I MUST ALWAYS REMEMBER:\n'
AI_MEM_FOOTER = '\n=== END   CORE RULES/MEMORY ===\n'

AI_HISTORY_HEADER = '\n=== IOSK PERSONAL CHAT HISTORY BEGIN ===\n'
AI_HISTORY_FOOTER = '\n=== END   IOSK PERSONAL CHAT HISTORY ===\n'


# 2. Time Formatting
def format_timedelta(td: timedelta, style: str) -> str:
    """
    Consolidated helper to format timedelta objects for different commands.
    
    Styles:
      'ps':          "2m 15s"
      'top_process': "75:30"
      'uptime':      "1 day, 2:15" or "3:45" or "15 min" or "30s"
    """
    total_seconds = int(td.total_seconds())

    if style == 'ps':
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}m {seconds}s"

    if style == 'top_process':
        minutes, seconds = divmod(total_seconds, 60)
        return f"{minutes}:{seconds:02d}"

    if style == 'uptime':
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            day_str = f"{days} day{'s' if days > 1 else ''}"
            return f"{day_str}, {hours}:{minutes:02d}"
        if hours > 0:
            return f"{hours}:{minutes:02d}"
        if minutes > 0:
            return f"{minutes} min"
        return f"{td.seconds}s"
    
    # Fallback to default string representation if style is unknown
    return str(td)


# 3. Remote Command Dispatching
async def dispatch_remote_if_needed(io, command_name, argv):
    """
    Parses a user.host argument, dispatches the command to a remote peer if needed.

    Returns:
        A tuple (dispatched, result).
        - (True, bool): If dispatched, result is the success status of the remote call.
        - (False, list): If local, result is the (potentially modified) argv list.
    """
    user_arg_index = -1
    # Determine which argument might contain the user.host string
    if command_name == 'attach' and len(argv) > 1:
        user_arg_index = 1
    elif command_name in ['detach', 'unpause'] and len(argv) == 1:
        user_arg_index = 0
    elif command_name == 'pause' and len(argv) == 1: # 'pause' can have 0 args
        user_arg_index = 0

    if user_arg_index == -1:
        return False, argv  # Not a candidate for remote dispatch

    target_user_str = argv[user_arg_index]

    if '.' not in target_user_str:
        return False, argv

    parts = target_user_str.rsplit('.', 1)
    if len(parts) != 2:
         return False, argv
         
    potential_user, potential_host = parts

    is_remote_request = (
        io.os.port and
        potential_host != io.os.hostname and
        potential_host in io.os.port.routing_table
    )

    if is_remote_request:
        remote_argv = list(argv)
        remote_argv[user_arg_index] = potential_user
        
        # Reconstruct command string for remote execution
        if command_name in ['pause', 'unpause', 'detach']:
            # These simple commands only need the user on the remote side
            command_str = f"{command_name} {shlex.quote(potential_user)}"
        else: # For 'attach' and any future multi-argument commands
            command_str = f"{command_name} {' '.join(shlex.quote(arg) for arg in remote_argv)}"

        await io.print(f":: dispatching to {potential_host}: {command_str}")
        result = await io.os.port.stream_remote_exec(potential_host, command_str, io)
        return True, result

    if potential_host == io.os.hostname:
        # It's explicitly for the local host, so strip the host part
        new_argv = list(argv)
        new_argv[user_arg_index] = potential_user
        return False, new_argv

    return False, argv