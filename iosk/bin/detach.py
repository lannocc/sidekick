from os.path import join

async def iocall(io, argv):
    """Detach a user from a device.

    Usage: detach <handle>
           attach --help
    """

    if not argv:
        await io.error('!! 1 argument required: <handle>')
        return

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    handle = argv[0]

    if not io.os.chat:
        await io.error('!! no chat')
        return

    if handle not in io.os.users:
        await io.error(f'!! not attached: {handle}')
        return

    return await io.os.chat.leave(io.os.users[handle])

