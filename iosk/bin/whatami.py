# ./bin/whatami.py

async def iocall(io, argv):
    """Display the name of the current device.

    Usage: whatami
           whatami --help

    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if argv:
        await io.error("!! whatami: does not accept arguments. Use 'whatami --help' for usage.")
        return False

    device_name = io.dev
    # Strip '/dev/' prefix if present
    if device_name.startswith('/dev/'):
        device_name = device_name[len('/dev/'):]
    await io.print(device_name)

    return True
