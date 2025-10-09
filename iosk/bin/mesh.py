import asyncio

DOCSTRING = """Connect to other IOSK systems or view the current network mesh.

Usage: mesh
       mesh <host[:port]>
       mesh --help

mesh:
  Lists all currently connected peer systems in the network mesh, including
  both direct and indirect (routed) connections.

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
        # Get the routing table from the port manager.
        routing_table = port_manager.routing_table

        # Create a list to hold display data for all systems in the mesh.
        display_list = []

        # Add our own system's info first.
        our_hostname = io.os.hostname
        if port_manager.port is not None:
            our_hostname += "*"  # Indicate that the listening port is open.
        display_list.append({'hostname': our_hostname, 'address': ''})

        # Process all known peers from the routing table.
        peer_list = []
        for hostname, route_info in routing_table.items():
            address_str = ''
            route_type = route_info.get('type')

            if route_type == 'direct':
                websocket = route_info.get('websocket')
                if websocket and hasattr(websocket, 'remote_address'):
                    address_str = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
                else:
                    address_str = "[direct - error]"
            elif route_type == 'indirect':
                via_host = route_info.get('via')
                if via_host:
                    address_str = f"[via {via_host}]"
                else:
                    address_str = "[indirect - error]"
            else:
                address_str = f"[unknown route type: {route_type}]"

            peer_list.append({'hostname': hostname, 'address': address_str})

        # Sort peers alphabetically by hostname and add to the main display list.
        display_list.extend(sorted(peer_list, key=lambda x: x['hostname']))

        # Dynamically calculate column widths for clean formatting.
        max_host_len = len("HOSTNAME")
        for system in display_list:
            if len(system['hostname']) > max_host_len:
                max_host_len = len(system['hostname'])

        # Add padding
        max_host_len += 2

        # Print the formatted table.
        await io.print(f"{'HOSTNAME':<{max_host_len}} ADDRESS")
        await io.print(f"{'-' * max_host_len} {'-' * 20}")

        for system in display_list:
            await io.print(f"{system['hostname']:<{max_host_len}} {system['address']}")

        # The total count is the local host plus all known peers.
        count = 1 + len(routing_table)
        await io.print(f"\n:: {count} system{'s' if count != 1 else ''} in mesh.")
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

