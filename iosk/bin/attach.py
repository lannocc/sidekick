import posixpath
from src.iosk.util import dispatch_remote_if_needed

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

    # Check for and handle remote dispatch
    dispatched, result = await dispatch_remote_if_needed(io, 'attach', argv)
    if dispatched:
        return result
    argv = result  # Update argv with hostname stripped if necessary

    device = argv[0]
    handle_arg = argv[1] if len(argv) > 1 else None
    
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