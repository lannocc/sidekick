#!/usr/bin/env python
# bin/whereami.py

DOCSTRING = """Display the configured hostname and active room of the local IOSK system.

Usage: whereami
       whereami --help

Displays the unique hostname of the local IOSK system on the network.
If a chat room is active, its name is appended, e.g., 'hostname/room_name'.
"""

async def iocall(io, argv):
    """Handle the 'whereami' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if argv:
        await io.error("!! whereami: command takes no arguments. Use 'whereami --help'.")
        return False

    # The kernel reads /etc/hostname at startup and stores the result.
    hostname = io.os.hostname
    output = hostname

    # Check for an active chat room and append it if it exists.
    if hasattr(io.os, 'chat') and io.os.chat and io.os.chat.active_room:
        room_name = io.os.chat.active_room
        output = f"{hostname}/{room_name}"

    await io.print(output)

    return True
