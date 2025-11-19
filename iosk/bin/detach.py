import shlex

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

    handle_arg = argv[0]

    if '.' in handle_arg:
        parts = handle_arg.rsplit('.', 1)
        if len(parts) == 2:
            potential_user, potential_host = parts
            
            is_remote_request = (
                io.os.port and
                potential_host != io.os.hostname and
                potential_host in io.os.port.routing_table
            )

            if is_remote_request:
                command_str = f"detach {shlex.quote(potential_user)}"
                await io.print(f":: dispatching to {potential_host}: {command_str}")
                return await io.os.port.stream_remote_exec(potential_host, command_str, io)

            if potential_host == io.os.hostname:
                # It's explicitly for the local host, so strip the host part
                handle_arg = potential_user

    # --- Local Execution ---

    handle = handle_arg

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