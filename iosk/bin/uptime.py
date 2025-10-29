from datetime import datetime

DOCSTRING = """Show how long the system has been running.

Usage: uptime
       uptime --help

Displays the current time, how long the system has been running,
and how many users are currently logged on.
"""

def format_uptime(td):
    """Formats uptime timedelta similar to standard `top` command."""
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        day_str = f"{days} day{'s' if days > 1 else ''}"
        # uptime format is like "X days, HH:MM"
        return f"{day_str}, {hours}:{minutes:02d}"

    # or just "HH:MM" if less than a day
    if hours > 0:
        return f"{hours}:{minutes:02d}"

    # or just "X min" if less than an hour
    if minutes > 0:
        return f"{minutes} min"

    return f"{td.seconds}s"


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
        uptime_str = format_uptime(now - io.os.started)

    # 3. User count
    user_count = len(io.os.users)
    user_str = f"{user_count} user{'s' if user_count != 1 else ''}"

    # Assemble the final output string, similar to Linux `uptime`
    # Example: " 10:42:37 up 5 min,  1 user
    await io.print(f" {now_str} up {uptime_str},  {user_str}")

    return True

