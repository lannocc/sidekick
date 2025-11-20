import asyncio
from datetime import datetime
from sk.iosk.util import format_timedelta

DOCSTRING = """Provide a single, non-interactive snapshot of system activity.

Usage: top
       top --help

Displays a summary of system status and a list of running processes,
sorted by runtime in descending order. This is a one-shot command
and does not update in real-time.
"""

async def iocall(io, argv):
    """
    Handle the 'top' command execution.
    """
    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    # --- 1. Gather Summary Data ---
    now = datetime.now()
    
    # Uptime calculation
    uptime = "unknown"
    if io.os.started:
        uptime = format_timedelta(now - io.os.started, style='uptime')

    # User and process counts
    total_users = len(io.os.users.contexts)
    process_table = io.os.proc.process_table
    total_procs = len(process_table)
    
    # --- 2. Print Summary ---
    now_str = now.strftime('%H:%M:%S')
    await io.print(f"top - {now_str} up {uptime},  {total_users} user{'s' if total_users != 1 else ''},  load average: N/A")
    await io.print(f"Tasks: {total_procs} total")
    await io.print("") # Blank line before process list

    if not total_procs:
        return True # Nothing more to do

    # --- 3. Gather and Sort Process Data ---
    process_data = []
    
    for proc in process_table.values():
        runtime = now - proc.start_time
        process_data.append((proc, runtime))
    
    # Sort by runtime, descending
    sorted_processes = sorted(process_data, key=lambda x: x[1], reverse=True)

    # Calculate column widths from sorted data
    display_data = []
    max_pid_width = len("PID")
    max_user_width = len("USER")

    for proc, runtime in sorted_processes:
        pid_str = str(proc.pid)
        user_str = proc.user
        time_str = format_timedelta(runtime, style='top_process')
        cmd_str = proc.command_str
        
        display_data.append((pid_str, user_str, time_str, cmd_str))
        
        if len(pid_str) > max_pid_width:
            max_pid_width = len(pid_str)
        if len(user_str) > max_user_width:
            max_user_width = len(user_str)
            
    # --- 4. Print Header ---
    header = (
        f'{"PID":>{max_pid_width}} '
        f'{"USER":<{max_user_width}}  '
        f'{"TIME+":>8} ' # TIME+ column with fixed width, right-aligned content
        f'COMMAND'
    )
    await io.print(header)

    # --- 5. Print Process List ---
    for pid_str, user_str, time_str, cmd_str in display_data:
        row = (
            f'{pid_str:>{max_pid_width}} '
            f'{user_str:<{max_user_width}}  '
            f'{time_str:>8} '
            f'{cmd_str}'
        )
        await io.print(row)
        
    return True
