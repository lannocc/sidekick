import asyncio

DOCSTRING = """Connect to other IOSK systems or view the current network mesh.

Usage: mesh
       mesh <host[:port]>
       mesh --help

mesh:
  Lists all currently connected peer systems in the network mesh.

mesh <host[:port]>:
  Establishes an outbound connection to another IOSK system's listener
  service. If the port is not specified, it defaults to 4209.

--help:
  Displays this help message.
"""

async def iocall(io, argv):
    """Handle the 'mesh' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    # Check for the kernel's port manager subsystem.
    if not hasattr(io.os, 'port') or not io.os.port:
        await io.error("!! mesh: network subsystem is not available.")
        return False

    port_manager = io.os.port

    # Case 1: 'mesh' (status check)
    if not argv:
        if not port_manager.peers:
            await io.print(":: No peers connected.")
            return True

        # Print header
        await io.print(f"{'HOSTNAME':<20} ADDRESS")
        await io.print(f"{'-'*20} {'-'*20}")

        # Print each peer's information
        for hostname, websocket in sorted(port_manager.peers.items()):
            address = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
            await io.print(f"{hostname:<20} {address}")

        count = len(port_manager.peers)
        await io.print(f"\n:: {count} peer{'s' if count != 1 else ''} connected.")
        return True

    # Case 2: 'mesh <host[:port]>' (connect to peer)
    if len(argv) == 1:
        host_arg = argv[0]
        
        # Parse host and port
        if ':' in host_arg:
            host, port_str = host_arg.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                await io.error(f"!! mesh: invalid port number '{port_str}'")
                return False
        else:
            host = host_arg
            port = 4209 # Default port

        # Construct WebSocket URI
        uri = f"ws://{host}:{port}"
        
        await io.print(f":: Connecting to {host}:{port}...")
        
        # The connect_to_peer method runs the connection handler in the background.
        # It handles its own error reporting. We just initiate the connection.
        await port_manager.connect_to_peer(uri)
        
        # The user can run 'mesh' again after a moment to verify the connection.
        return True

    # Case 3: Too many arguments
    await io.error("!! mesh: too many arguments. Use 'mesh --help' for usage.")
    return False
