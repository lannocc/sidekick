import posixpath
import shlex

async def iocall(io, argv):
    """Attach a device as a user.

    Usage: attach <device> [handle[.host]]
           attach --help
    """

    if not argv or len(argv) < 1 or len(argv) > 2:
        await io.error('!! 1-2 arguments required: <device> [handle]')
        return

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    device = argv[0]
    handle_arg = argv[1] if len(argv) > 1 else None

    if handle_arg and '.' in handle_arg:
        parts = handle_arg.rsplit('.', 1)
        if len(parts) == 2:
            potential_user, potential_host = parts
            
            is_remote_request = (
                io.os.port and
                potential_host != io.os.hostname and
                potential_host in io.os.routing_table
            )

            if is_remote_request:
                command_str = f"attach {shlex.quote(device)} {shlex.quote(potential_user)}"
                await io.print(f":: dispatching to {potential_host}: {command_str}")
                return await io.os.port.stream_remote_exec(potential_host, command_str, io)

            if potential_host == io.os.hostname:
                # It's explicitly for the local host, so strip the host part
                handle_arg = potential_user
    
    # --- Local Execution ---

    if not io.os.chat:
        await io.error('!! no chat')
        return

    handle = handle_arg if handle_arg is not None else device
    handle = handle.replace('/', '-')

    device_path = posixpath.join('/dev', device)

    new_io = await io.os.chat.join(handle, device_path)

    if new_io:
        await io.os.system.print(f":: {io.user} attached user '{handle}' to device '{device_path}'")
        return True
    else:
        # The join call would have already printed an error to the user's io.
        await io.os.system.print(f":: {io.user} FAILED to attach user '{handle}' to device '{device_path}'")
        return False