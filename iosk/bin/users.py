async def iocall(io, args):
    """List connected users.

    Usage: users
           users --help

    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not io.os.users:
        await io.print(':: no users are connected')
        return

    await io.print(' '.join(io.os.users.keys()))
    count = len(io.os.users)
    await io.print(f':: {count} user{"s" if count != 1 else ""} connected')

