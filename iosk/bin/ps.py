import asyncio
from datetime import datetime
from sk.iosk.util import format_timedelta

DOCSTRING = """List currently running processes.

Usage: ps
       ps --help

Displays information about active processes, including their PID,
the user who started them, their running time, and the command.
"""

async def iocall(io, argv):
    """
    Handle the 'ps' command execution.
    This function accesses the kernel's process table and prints a formatted
    list of all currently running command processes.
    """
    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    process_table = io.os.proc.process_table
    if not process_table:
        await io.print(":: no active processes")
        return True

    # Prepare data for printing and calculate dynamic column widths for alignment
    now = datetime.now()
    process_data = []
    max_pid_width = len("PID")
    max_user_width = len("USER")

    # Sort processes by PID for consistent, predictable output
    sorted_pids = sorted(process_table.keys())

    for pid in sorted_pids:
        proc = process_table[pid]
        
        pid_str = str(proc.pid)
        user_str = proc.user
        time_str = format_timedelta(now - proc.start_time, style='ps')
        cmd_str = proc.command_str

        process_data.append((pid_str, user_str, time_str, cmd_str))

        if len(pid_str) > max_pid_width:
            max_pid_width = len(pid_str)
        if len(user_str) > max_user_width:
            max_user_width = len(user_str)
    
    # Print the formatted header row
    header = (
        f'{"PID":<{max_pid_width}}  '
        f'{"USER":<{max_user_width}}  '
        f'{"TIME":<8}  '  # TIME column has a relatively fixed-width format
        f'COMMAND'
    )
    await io.print(header)

    # Print each process row with aligned columns
    for pid_str, user_str, time_str, cmd_str in process_data:
        row = (
            f'{pid_str:<{max_pid_width}}  '
            f'{user_str:<{max_user_width}}  '
            f'{time_str:<8}  '
            f'{cmd_str}'
        )
        await io.print(row)

    return True
