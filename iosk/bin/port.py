async def iocall(io, argv):
    """Controls the network listener service.

    Usage: port
           port on [port_num]
           port off
           port --help

    port:
      Displays the current status of the network listener.

    port on [port_num]:
      Starts the listener service on the specified port. Defaults to 4209.

    port off:
      Stops the listener service and closes all connections.

    --help:
      Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__.strip())
        return True

    # Check for the kernel's port manager subsystem.
    if not hasattr(io.os, 'port') or not io.os.port:
        await io.error("!! port manager subsystem not available.")
        return False

    port_manager = io.os.port

    # Case 1: No arguments -> 'port' (status check)
    if not argv:
        if port_manager.port is not None:
            await io.print(f":: port {port_manager.port} open")
        else:
            await io.print(":: port closed")
        return True

    command = argv[0]

    # Case 2: 'port on [port_num]'
    if command == 'on':
        if len(argv) > 2:
            await io.error("!! port on: too many arguments")
            return False

        port_num = 4209  # Default port
        if len(argv) == 2:
            try:
                port_num = int(argv[1])
                if not (0 < port_num < 65536):
                    raise ValueError("Port out of range")
            except ValueError:
                await io.error(f"!! port on: invalid port number '{argv[1]}'")
                return False

        if await port_manager.start(port_num):
            await io.print(f":: port {port_num} opened")
            return True
        else:
            # The port_manager.start method will print its own error on failure.
            return False

    # Case 3: 'port off'
    elif command == 'off':
        if len(argv) > 1:
            await io.error("!! port off: command takes no arguments")
            return False

        await port_manager.stop()
        await io.print(":: port service stopped.")
        return True

    # Case 4: Invalid command
    else:
        await io.error(f"!! port: unknown command '{command}'. Use 'on', 'off', or see 'port --help'.")
        return False
