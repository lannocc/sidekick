from datetime import datetime
from sk.iosk.util import format_timedelta

DOCSTRING = """Show how long the system has been running.

Usage: uptime
       uptime --help

Displays the current time, how long the system has been running,
and how many users are currently logged on.
"""

async def iocall(io, argv):
    """Handle the 'uptime' command execution."""
    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if argv:
        await io.error("!! uptime: does not accept arguments. Use 'uptime --help' for usage.")
        return False

    now = datetime.now()

    # 1. Current time
    now_str = now.strftime('%H:%M:%S')

    # 2. Uptime string
    uptime_str = "unknown"
    if io.os.started:
        uptime_str = format_timedelta(now - io.os.started, style='uptime')

    # 3. User count
    user_count = len(io.os.users.contexts)
    user_str = f"{user_count} user{'s' if user_count != 1 else ''}"

    # Assemble the final output string, similar to Linux `uptime`
    # Example: " 10:42:37 up 5 min,  1 user
    await io.print(f" {now_str} up {uptime_str},  {user_str}")

    return True