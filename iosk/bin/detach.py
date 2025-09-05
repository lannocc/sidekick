from os.path import join

async def iocall(io, args):
    """Detach a user from a device.

    Usage: detach <handle>
           attach --help
    """

    if args:
        handle = args

    else:
        await io.error('!! 1 argument required: <handle>')
        return

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not io.os.chat:
        await io.error('!! no chat')
        return

    if handle not in io.os.users:
        await io.error(f'!! not attached: {handle}')
        return

    return await io.os.chat.leave(io.os.users[handle])

