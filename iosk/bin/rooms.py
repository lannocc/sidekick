import os

DOCSTRING = """List all rooms created on the local system.

Usage: rooms [-v | --verbose]
       rooms --help

Lists all rooms that have been created on the local system by listing
the directories in /var/room/. The currently active room, if any, is
indicated with a leading asterisk (*), followed by the count of active
users in parentheses, e.g., '*iosk(2)'.

Options:
  -v, --verbose    Use a verbose, multi-column format showing ROOM and TOPIC.
  --help           Displays this help message.
"""

async def iocall(io, argv):
    """Handle the 'rooms' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    verbose = False
    if '-v' in argv:
        verbose = True
        argv.remove('-v')
    if '--verbose' in argv:
        verbose = True
        argv.remove('--verbose')

    if argv:
        await io.error("!! rooms: command takes no arguments other than -v/--verbose.")
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

    # Get the active room name and count of local users in it
    active_room_name = None
    local_active_user_count = 0
    if io.os.chat:
        active_room_name = io.os.chat.active_room
        if active_room_name: # If a room is active locally
            local_active_user_count = len(io.os.users) # All local users are in the active room

    room_data = []

    # 1. Gather data for all rooms
    for name in room_names:
        topic_path = f'/var/room/{name}/topic'
        topic_content = await io.os.get(io, topic_path)
        topic = topic_content.strip() if topic_content else '(none)'

        is_active = (name == active_room_name)
        current_room_user_count = local_active_user_count if is_active else 0

        room_data.append({
            'name': name,
            'topic': topic,
            'users': current_room_user_count,
            'is_active': is_active
        })

    if not verbose:
        # Non-verbose output
        for data in room_data:
            display_name = data['name']
            if data['is_active']:
                display_name = f"*{display_name}"
            await io.print(display_name)
    else:
        # Verbose, multi-column output
        # 2. Calculate dynamic column widths
        max_room_len = len("ROOM")
        max_topic_len = len("TOPIC")

        for data in room_data:
            display_name = data['name']
            if data['is_active']:
                display_name = f"*{display_name}[{data['users']}]" # Includes count in name for active room
            
            if len(display_name) > max_room_len:
                max_room_len = len(display_name)
            if len(data['topic']) > max_topic_len:
                max_topic_len = len(data['topic'])

        # 3. Print Header
        await io.print(f"{'ROOM':<{max_room_len}}  {'TOPIC':<{max_topic_len}}")

        # 4. Print Separator
        await io.print(f"{'-'*max_room_len}  {'-'*max_topic_len}")

        # 5. Print Data Rows
        for data in room_data:
            display_name = data['name']
            if data['is_active']:
                display_name = f"*{display_name}({data['users']})" # Same logic as for max_room_len
            
            await io.print(f"{display_name:<{max_room_len}}  {data['topic']:<{max_topic_len}}")
    
    # Final count
    count = len(room_names)
    if verbose:
        await io.print("") # Add a newline before the final count for better spacing

    await io.print(f":: {count} room{'s' if count != 1 else ''} found.")

    return True

