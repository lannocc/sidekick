async def iocall(io, args):
    """Shut down the system.

    Usage: shutdown
           shutdown --help

    --help: Displays this help message.
    """
    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    io.os.halt.set()

