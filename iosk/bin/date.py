from datetime import datetime

async def iocall(io, args):
    """Display the current date and time.

    Usage: date
           date --help

    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    await io.print(datetime.now().strftime('%A, %b %d, %Y at %I:%M %p'))
    return True

