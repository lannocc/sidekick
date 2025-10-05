from os.path import join

async def iocall(io, argv):
    """Detach a device user.

    Usage: detach <handle>
           detach --help
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

    target_io = io.os.users[handle]
    device_path = target_io.dev # Capture device before leaving

    success = await io.os.chat.leave(target_io)

    if success:
        await io.os.system.print(f":: {io.user} detached user '{handle}' from device '{device_path}'")
    else:
        # The leave call likely prints its own error to the user's io.
        await io.os.system.print(f":: {io.user} FAILED to detach user '{handle}'")

    return success

