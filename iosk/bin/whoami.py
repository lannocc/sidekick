async def iocall(io, args):
    """Display the current username.

    Usage: whoami
           whoami --help

    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    await io.print(io.user)
    return True
