from os.path import join

async def iocall(io, args):
    """Attach a user to a device.

    Usage: attach <device> [handle]
           attach --help
    """

    if args:
        args = args.split(' ')

    else:
        await io.error('!! 1-2 arguments required: <device> [handle]')
        return

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not io.os.chat:
        await io.error('!! no chat')
        return

    device = args[0]
    handle = args[1] if len(args) > 1 else device
    handle = handle.replace('/', '-')

    io = await io.os.chat.join(handle, join('/dev', device))
    return True if io else False

