#!/usr/bin/env python
# bin/where.py

DOCSTRING = """Display a list of all known users across the network mesh.

Usage: where [-v | --verbose]
       where --help

By default, displays a compact list of users in the format 'user.host/room'.
If a user is not in a room, the '/room' part is omitted.

Options:
  -v, --verbose    Use a verbose, multi-column format with headers.
                   The columns are USER, HOST, and ROOM.
  --help           Displays this help message.
"""

async def iocall(io, argv):
    """Handle the 'where' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    # --- Argument Parsing ---
    verbose = False
    if '-v' in argv:
        verbose = True
        argv.remove('-v')
    if '--verbose' in argv:
        verbose = True
        argv.remove('--verbose')

    if argv:
        await io.error("!! where: command takes no arguments other than -v/--verbose.")
        return False

    # --- Data Gathering ---
    network_users = io.os.network_users
    network_rooms = getattr(io.os, 'network_rooms', {})

    if not network_users:
        await io.print(":: No users found across the mesh.")
        return True

    user_data = []
    for user_addr in network_users.keys():
        if '.' in user_addr:
            user, host = user_addr.split('.', 1)
        else:
            user = user_addr
            host = io.os.hostname

        # Get the room; will be None if the user isn't in a networked room
        room = network_rooms.get(user_addr)
        user_data.append((user, host, room))

    # Sort for consistent, readable output (by host, then room, then by user)
    # The `or ''` ensures that None values for rooms sort correctly and consistently.
    sorted_data = sorted(user_data, key=lambda x: (x[1], x[2] or '', x[0]))

    # --- Output Generation ---
    if verbose:
        # Verbose, multi-column output
        max_user_len = len("USER")
        max_host_len = len("HOST")
        max_room_len = len("ROOM")

        for user, host, room in sorted_data:
            if len(user) > max_user_len: max_user_len = len(user)
            if len(host) > max_host_len: max_host_len = len(host)
            # Use display-friendly version for length calculation
            if room and len(room) > max_room_len: max_room_len = len(room)

        # Print Header (new order: USER HOST ROOM)
        await io.print(f"{'USER':<{max_user_len}}  {'HOST':<{max_host_len}}  {'ROOM':<{max_room_len}}")

        # Print Separator
        await io.print(f"{'-'*max_user_len}  {'-'*max_host_len}  {'-'*max_room_len}")

        # Print Data Rows
        for user, host, room in sorted_data:
            display_room = room or '(none)'
            await io.print(f"{user:<{max_user_len}}  {host:<{max_host_len}}  {display_room:<{max_room_len}}")

    else:
        # Default, sparse output
        for user, host, room in sorted_data:
            line = f"{user}.{host}"
            if room:
                line += f"/{room}"
            await io.print(line)

    # --- Final Count ---
    count = len(sorted_data)
    # Add a newline before the final count only in verbose mode for better spacing
    if verbose:
        await io.print("")

    await io.print(f":: {count} user{'s' if count != 1 else ''} found across the mesh.")

    return True

