#!/usr/bin/env python
# bin/where.py

DOCSTRING = """Display a list of all known users and their rooms across the network mesh.

Usage: where
       where --help

Displays each user, the room they are in, and the hostname of the system
they are connected to.
"""

async def iocall(io, argv):
    """Handle the 'where' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if argv:
        await io.error("!! where: command takes no arguments. Use 'where --help'.")
        return False

    network_users = io.os.network_users
    # Assume network_rooms is a dict mapping 'user.host' to 'room_name'.
    # Use getattr for safety in case the attribute doesn't exist.
    network_rooms = getattr(io.os, 'network_rooms', {})

    if not network_users:
        await io.print(":: No users found across the mesh.")
        return True

    # Prepare data for formatting, including the user's room.
    user_data = []
    for user_addr in network_users.keys():
        if '.' in user_addr:
            user, host = user_addr.split('.', 1)
        else:
            # Fallback for a user address without a host part; assume local.
            user = user_addr
            host = io.os.hostname
        
        room = network_rooms.get(user_addr, '(none)')
        user_data.append((user, room, host))

    # Calculate dynamic column widths for alignment, including headers
    max_user_len = len("USER")
    max_room_len = len("ROOM")
    max_host_len = len("HOST")

    for user, room, host in user_data:
        if len(user) > max_user_len:
            max_user_len = len(user)
        if len(room) > max_room_len:
            max_room_len = len(room)
        if len(host) > max_host_len:
            max_host_len = len(host)

    # Sort for consistent, readable output (by host, then room, then by user)
    sorted_data = sorted(user_data, key=lambda x: (x[2], x[1], x[0]))

    # --- Print the formatted table ---

    # Header
    await io.print(f"{'USER':<{max_user_len}}  {'ROOM':<{max_room_len}}  {'HOST':<{max_host_len}}")

    # Separator
    await io.print(f"{'-'*max_user_len}  {'-'*max_room_len}  {'-'*max_host_len}")

    # Data Rows
    for user, room, host in sorted_data:
        await io.print(f"{user:<{max_user_len}}  {room:<{max_room_len}}  {host:<{max_host_len}}")

    # Final Count
    count = len(sorted_data)
    await io.print(f"\n:: {count} user{'s' if count != 1 else ''} found across the mesh.")

    return True
