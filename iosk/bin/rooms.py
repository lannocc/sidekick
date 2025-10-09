import os

DOCSTRING = """List all rooms created on the local system.

Usage: rooms
       rooms --help

Lists all rooms that have been created on the local system by listing
the directories in /var/room/. The currently active room, if any, is
indicated with a leading asterisk (*).
"""

async def iocall(io, argv):
    """Handle the 'rooms' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if argv:
        await io.error("!! rooms: command takes no arguments. Use 'rooms --help'.")
        return False

    room_dir_virtual = '/var/room'
    room_dir_host = io.os.box(room_dir_virtual, io_context=io)

    if not os.path.exists(room_dir_host) or not os.path.isdir(room_dir_host):
        await io.print(":: No rooms found.")
        return True

    try:
        # Get all entries in the directory and filter for subdirectories
        room_names = sorted([
            name for name in os.listdir(room_dir_host)
            if os.path.isdir(os.path.join(room_dir_host, name))
        ])
    except OSError as e:
        await io.error(f"!! rooms: failed to read rooms directory: {e}")
        return False

    if not room_names:
        await io.print(":: No rooms found.")
        return True

    # Get the active room from the chat subsystem
    active_room = None
    if io.os.chat:
        active_room = io.os.chat.active_room

    # Print each room, marking the active one
    for name in room_names:
        if name == active_room:
            await io.print(f"*{name}")
        else:
            await io.print(name)
    
    # Print the final count
    count = len(room_names)
    await io.print(f":: {count} room{'s' if count != 1 else ''} found.")

    return True
