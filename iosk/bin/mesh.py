import asyncio

DOCSTRING = """Connect to other IOSK systems or view the current network mesh.

Usage: mesh [-s | --simple]
       mesh <host[:port]>
       mesh --help

mesh:
  Lists all currently connected peer systems in the network mesh, including
  both direct and indirect (routed) connections. The local system's hostname
  is prepended with a tilde (~). If the local system has its listener port
  open, an asterisk (*) is appended to its hostname.

  Options:
    -s, --simple     Use a compact, single-column format: 'hostname'.
                     The local host is indicated by a leading tilde (~), and
                     an asterisk (*) if its listener is open. Address details
                     like '[ip:port]' or '[via host]' are omitted in this mode.

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

    # --- Argument Parsing for status command options ---
    simple_mode = False
    cleaned_argv = []
    for arg in argv:
        if arg == '-s' or arg == '--simple':
            simple_mode = True
        else:
            cleaned_argv.append(arg)
    argv = cleaned_argv

    # Case 1: 'mesh' (status check) - after options are parsed
    if not argv:
        mesh_items = [] # Stores structured data for all systems

        # Add our own system's info
        local_hostname = io.os.hostname
        is_listening = (port_manager.port is not None)
        local_address = ""
        if is_listening:
            # For the local host, show the listening bind address and port.
            bind_host = getattr(port_manager, 'host', '0.0.0.0')
            local_address = f"{bind_host}:{port_manager.port}"

        mesh_items.append({
            'hostname': local_hostname,
            'is_local': True,
            'is_listening': is_listening,
            'address': local_address,
            'route_type': 'local' # Custom type for local entry
        })

        # Process all known peers from the routing table.
        for hostname, route_info in port_manager.routing_table.items():
            address_str = ''
            route_type = route_info.get('type')

            if route_type == 'direct':
                websocket = route_info.get('websocket')
                if websocket and hasattr(websocket, 'remote_address'):
                    address_str = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
                # If direct but no remote_address, address_str remains empty
            elif route_type == 'indirect':
                via_host = route_info.get('via')
                if via_host:
                    # Keep this format for indirect routes
                    address_str = f"[via {via_host}]"
                else:
                    address_str = "[indirect - error]"
            # For simple mode, indirect/unknown connections will not show an address part if empty.

            mesh_items.append({
                'hostname': hostname,
                'is_local': False,
                'is_listening': False, # We don't know if a peer is listening from this context
                'address': address_str,
                'route_type': route_type
            })

        # Sort all items by hostname
        sorted_mesh_items = sorted(mesh_items, key=lambda x: x['hostname'])

        # Ensure local host is always first in the display
        # Find the local entry and move it to the front if it's not already.
        local_entry_idx = -1
        for i, item in enumerate(sorted_mesh_items):
            if item['is_local']:
                local_entry_idx = i
                break
        if local_entry_idx > 0:
            local_entry = sorted_mesh_items.pop(local_entry_idx)
            sorted_mesh_items.insert(0, local_entry)


        if simple_mode:
            # Simple output format: ~hostname* or hostname
            for item in sorted_mesh_items:
                display_line_parts = []
                if item['is_local']:
                    display_line_parts.append('~')

                display_line_parts.append(item['hostname'])

                if item['is_local'] and item['is_listening']:
                    display_line_parts.append('*')

                # Removed: Address part for simple mode is no longer desired.
                # The prompt explicitly states: "we no longer want the [address:port] or [via hostname] part."
                #
                # address_part = ""
                # if item['is_local'] and item['is_listening'] and item['address'] and ':' in item['address']:
                #     address_part = f"[{item['address']}]"
                # elif item['route_type'] == 'direct' and item['address'] and ':' in item['address']:
                #     address_part = f"[{item['address']}]"
                # elif item['route_type'] == 'indirect' and item['address']:
                #     address_part = item['address']
                #
                # if address_part:
                #     display_line_parts.append(address_part)
                
                await io.print("".join(display_line_parts))
            # No final count in simple mode, consistent with rooms and where.

        else:
            # Verbose output format (existing table)
            # Dynamically calculate column widths for clean formatting.
            max_host_len = len("HOSTNAME")
            max_address_len = len("ADDRESS")

            for item in sorted_mesh_items:
                hostname_display = item['hostname']
                if item['is_local']:
                    hostname_display = f"~{hostname_display}"
                    if item['is_listening']:
                        hostname_display += "*"

                if len(hostname_display) > max_host_len:
                    max_host_len = len(hostname_display)

                # The verbose output includes `[via host]` or `[indirect - error]` in the address.
                # So we consider the full `item['address']` for width calculation.
                if len(item['address']) > max_address_len:
                    max_address_len = len(item['address'])

            # Print the formatted table.
            await io.print(f"{'HOSTNAME':<{max_host_len}}  {'ADDRESS':<{max_address_len}}")
            await io.print(f"{'-' * max_host_len}  {'-' * max_address_len}")

            for item in sorted_mesh_items:
                hostname_display = item['hostname']
                if item['is_local']:
                    hostname_display = f"~{hostname_display}"
                    if item['is_listening']:
                        hostname_display += "*"

                await io.print(f"{hostname_display:<{max_host_len}}  {item['address']:<{max_address_len}}")

            # The total count is the local host plus all known peers.
            count = len(sorted_mesh_items)
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

    # Case 3: Too many arguments (after -s processing)
    await io.error("!! mesh: too many arguments. Use 'mesh --help' for usage.")
    return False

