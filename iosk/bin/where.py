#!/usr/bin/env python
# bin/where.py

DOCSTRING = """Display a list of all known users across the network mesh.

Usage: where [-v | --verbose]
       where --help

By default, displays a compact list of users in the format 'user.host/room'.
If a user is not in a room, the '/room' part is omitted.
For the local host, the '.host' part is omitted.
The user running the command is indicated with a leading asterisk (*).

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

    current_running_user = io.user
    local_hostname = io.os.hostname

    if not network_users:
        await io.print(":: No users found across the mesh.")
        return True

    user_data = [] # Stores (user, host, room, is_current_user, is_local_user)
    for user_addr in network_users.keys():
        user, host = user_addr.split('.', 1) if '.' in user_addr else (user_addr, local_hostname)

        is_local = (host == local_hostname)
        is_current = (user == current_running_user and is_local) # Only local user can be "current"

        room = network_rooms.get(user_addr)
        user_data.append((user, host, room, is_current, is_local))

    # Sort for consistent, readable output (by host, then room, then by user)
    # The `or ''` ensures that None values for rooms sort correctly and consistently.
    sorted_data = sorted(user_data, key=lambda x: (x[1], x[2] or '', x[0]))

    # --- Output Generation ---
    if verbose:
        # Verbose, multi-column output
        max_user_len = len("USER")
        max_host_len = len("HOST")
        max_room_len = len("ROOM")

        # Calculate dynamic column widths
        for user, host, room, is_current, is_local in sorted_data:
            display_user_str = f"*{user}" if is_current else user
            display_host_str = "" if is_local else host
            display_room_str = room or '(none)'

            if len(display_user_str) > max_user_len: max_user_len = len(display_user_str)
            if len(display_host_str) > max_host_len: max_host_len = len(display_host_str)
            if len(display_room_str) > max_room_len: max_room_len = len(display_room_str)

        # Print Header (new order: USER HOST ROOM)
        await io.print(f"{'USER':<{max_user_len}}  {'HOST':<{max_host_len}}  {'ROOM':<{max_room_len}}")

        # Print Separator
        await io.print(f"{'-'*max_user_len}  {'-'*max_host_len}  {'-'*max_room_len}")

        # Print Data Rows
        for user, host, room, is_current, is_local in sorted_data:
            display_user_str = f"*{user}" if is_current else user
            display_host_str = "" if is_local else host # Blank for local host
            display_room_str = room or '(none)'
            await io.print(f"{display_user_str:<{max_user_len}}  {display_host_str:<{max_host_len}}  {display_room_str:<{max_room_len}}")

    else:
        # Default, sparse output
        for user, host, room, is_current, is_local in sorted_data:
            line_parts = []
            if is_current:
                line_parts.append("*")

            line_parts.append(user)

            if not is_local:
                line_parts.append(f".{host}")

            if room:
                line_parts.append(f"/{room}")

            await io.print("".join(line_parts))

    # --- Final Count ---
    count = len(sorted_data)
    # Add a newline before the final count only in verbose mode for better spacing
    if verbose:
        await io.print("")

    await io.print(f":: {count} user{'s' if count != 1 else ''} found across the mesh.")

    return True

