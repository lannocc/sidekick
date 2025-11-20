import asyncio

DOCSTRING = """Disconnect from one or more peer IOSK systems.

Usage: unmesh [host...]
       unmesh --help

unmesh:
  Disconnects from all currently connected peer systems in the network mesh.

unmesh <host...>:
  Disconnects from the specified peer systems.

--help:
  Displays this help message.
"""

async def iocall(io, argv):
    """Handle the 'unmesh' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    # Check for the kernel's port manager subsystem.
    if not hasattr(io.os, 'port') or not io.os.port:
        await io.error("!! unmesh: network subsystem is not available.")
        return False

    port_manager = io.os.port

    # Case 1: 'unmesh' (disconnect from all peers)
    if not argv:
        # Create a copy of the peer hostnames to iterate over,
        # as the underlying dictionary will be modified during the loop.
        peer_hostnames = list(port_manager.peers.keys())

        if not peer_hostnames:
            await io.print(":: No peers to disconnect from.")
            return True

        await io.print(":: Disconnecting from all peers...")
        for host in peer_hostnames:
            # The websocket might already be gone if a disconnect happens
            # concurrently, so use .get() for safety.
            websocket = port_manager.peers.get(host)
            if websocket:
                try:
                    await websocket.close(1000, "User initiated disconnect")
                    # The PortManager's connection handler's `finally` block will
                    # perform the actual cleanup of state dictionaries.
                    await io.print(f":: Disconnection signal sent to '{host}'.")
                except Exception as e:
                    await io.error(f"!! unmesh: error disconnecting from '{host}': {e}")
        return True

    # Case 2: 'unmesh <host...>' (disconnect from specific peers)
    else:
        all_successful = True
        for host in argv:
            if host in port_manager.peers:
                websocket = port_manager.peers[host]
                try:
                    await websocket.close(1000, "User initiated disconnect")
                    await io.print(f":: Disconnection signal sent to '{host}'.")
                except Exception as e:
                    await io.error(f"!! unmesh: error disconnecting from '{host}': {e}")
                    all_successful = False
            else:
                await io.error(f"!! unmesh: not connected to peer '{host}'.")
                all_successful = False

        if all_successful:
            await io.print(":: Disconnection process completed.")
        else:
            await io.print(":: Disconnection process completed with errors.")

        return all_successful
