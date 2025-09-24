async def iocall(io, argv):
    """Display the current username.

    Usage: whoami
           whoami --help

    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    await io.print(io.user)
    return True
