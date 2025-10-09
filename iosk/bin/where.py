#!/usr/bin/env python
# bin/where.py

DOCSTRING = """Display a list of all known users across the network mesh.

Usage: where
       where --help

Displays each user and the hostname of the system they are connected to.
"""

async def iocall(io, argv):
    """Handle the 'where' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if argv:
        await io.error("!! where: command takes no arguments. Use 'where --help'.")
        return False

    # Access the network-wide user list from the kernel.
    # As per the proposal, this is the single source of truth for all users
    # across the mesh, including local ones.
    network_users = io.os.network_users

    if not network_users:
        await io.print(":: No users found across the mesh.")
        return True

    # Prepare data for formatting by splitting 'user.host' keys
    user_host_pairs = []
    for user_addr in network_users.keys():
        if '.' in user_addr:
            user, host = user_addr.split('.', 1)
            user_host_pairs.append((user, host))
        else:
            # Fallback for a user address without a host part; assume local.
            user = user_addr
            host = io.os.hostname
            user_host_pairs.append((user, host))

    # Calculate dynamic column widths for alignment, including headers
    max_user_len = len("USER")
    max_host_len = len("HOST")

    for user, host in user_host_pairs:
        if len(user) > max_user_len:
            max_user_len = len(user)
        if len(host) > max_host_len:
            max_host_len = len(host)

    # Sort for consistent, readable output (by host, then by user)
    sorted_users = sorted(user_host_pairs, key=lambda x: (x[1], x[0]))

    # --- Print the formatted table ---

    # Header
    await io.print(f"{'USER':<{max_user_len}}  {'HOST':<{max_host_len}}")

    # Separator
    await io.print(f"{'-'*max_user_len}  {'-'*max_host_len}")

    # Data Rows
    for user, host in sorted_users:
        await io.print(f"{user:<{max_user_len}}  {host:<{max_host_len}}")

    # Final Count
    count = len(sorted_users)
    await io.print(f"\n:: {count} user{'s' if count != 1 else ''} found across the mesh.")

    return True
