from sk.iosk.util import dispatch_remote_if_needed

async def iocall(io, argv):
    """Detach a device user.

    Usage: detach <handle[.host]>
           detach --help
    """

    if len(argv) != 1:
        await io.error('!! 1 argument required: <handle>')
        return

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    # Check for and handle remote dispatch
    dispatched, result = await dispatch_remote_if_needed(io, 'detach', argv)
    if dispatched:
        return result
    argv = result  # Update argv with hostname stripped if necessary

    handle_arg = argv[0]

    # --- Local Execution ---

    handle = handle_arg

    if not io.os.chat:
        await io.error('!! no chat')
        return

    if handle not in io.os.users.contexts:
        await io.error(f'!! not attached: {handle}')
        return

    target_io = io.os.users.contexts[handle]
    device_path = target_io.dev # Capture device before leaving

    success = await io.os.chat.leave(target_io)

    if success:
        await io.os.system.print(f":: {io.user} detached user '{handle}' from device '{device_path}'")
    else:
        # The leave call likely prints its own error to the user's io.
        await io.os.system.print(f":: {io.user} FAILED to detach user '{handle}'")

    return success
