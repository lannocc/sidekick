async def iocall(io, argv):
    """Display the current username or device.

    Usage: whoami [-d]
           whoami --help

    Displays the current username by default.

    Options:
      -d        Display the name of the current device.
      --help    Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not argv:
        # Default behavior: no arguments, print username
        await io.print(io.user)
        return True

    if len(argv) == 1 and argv[0] == '-d':
        # -d option: print device name
        device_name = io.dev
        # Strip '/dev/' prefix for cleaner output
        if device_name.startswith('/dev/'):
            device_name = device_name[len('/dev/'):]
        await io.print(device_name)
        return True

    # Handle invalid arguments
    await io.error(f"!! whoami: invalid argument '{' '.join(argv)}'. Use 'whoami --help' for usage.")
    return False

