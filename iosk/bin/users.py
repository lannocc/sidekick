async def iocall(io, argv):
    """List online users.

    Usage: users
           users --help

    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not io.os.users.contexts:
        await io.print(':: no users are online')
        return

    await io.print(' '.join(io.os.users.contexts.keys()))
    count = len(io.os.users.contexts)
    await io.print(f':: {count} user{"s" if count != 1 else ""} online')
