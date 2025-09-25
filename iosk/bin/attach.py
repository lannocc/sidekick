from os.path import join

async def iocall(io, argv):
    """Attach a device as a user.

    Usage: attach <device> [handle]
           attach --help
    """

    if not argv or len(argv) < 1 or len(argv) > 2:
        await io.error('!! 1-2 arguments required: <device> [handle]')
        return

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not io.os.chat:
        await io.error('!! no chat')
        return

    device = argv[0]
    handle = argv[1] if len(argv) > 1 else device
    handle = handle.replace('/', '-')

    io = await io.os.chat.join(handle, join('/dev', device))
    return True if io else False
