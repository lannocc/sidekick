# bin/sleep.py
import asyncio
import re

async def iocall(io, argv):
    """Pause execution for a specified amount of time.

    Usage: sleep <duration>...
           sleep --help

    Pauses for an amount of time specified by the sum of the values of
    the command line arguments. Each argument is a number followed by an
    optional unit. Default unit is seconds. This command only blocks its
    own execution; the user can still receive chat messages while it runs.

    Units:
      s - seconds (default)
      m - minutes
      h - hours
      d - days

    Example:
      sleep 10      # sleep for 10 seconds
      sleep 1.5m    # sleep for 1.5 minutes (90 seconds)
      sleep 1m 30s  # sleep for 1 minute and 30 seconds
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not argv:
        await io.error("!! sleep: missing operand")
        return False

    total_seconds = 0.0
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
    }
    
    for arg in argv:
        match = re.match(r'^(\d*\.?\d+)([smhd]?)$', arg)
        if not match:
            await io.error(f"!! sleep: invalid time interval '{arg}'")
            return False
            
        number_str, suffix = match.groups()
        
        try:
            number = float(number_str)
        except ValueError:
            await io.error(f"!! sleep: invalid number in interval '{arg}'")
            return False

        if not suffix:
            suffix = 's'
            
        total_seconds += number * multipliers[suffix]

    if total_seconds > 0:
        await asyncio.sleep(total_seconds)

    return True
