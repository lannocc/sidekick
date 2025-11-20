# bin/rooms.py
import os

DOCSTRING = """List all rooms created on the local system.

Usage: rooms [-s | --simple]
       rooms --help

By default, lists all rooms in a verbose, multi-column format showing ROOM and TOPIC.
The currently active room, if any, is indicated with a leading tilde (~),
followed by the count of active users in parentheses, e.g., '~iosk(2)'.

Options:
  -s, --simple     Use a compact, single-column format.
                   Active rooms are indicated with a leading tilde (~) and
                   user count, e.g., '~iosk(2)'.
  --help           Displays this help message.
"""

async def iocall(io, argv):
    """Handle the 'rooms' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    simple_mode = False
    # Check and remove -s or --simple arguments
    if '-s' in argv:
        simple_mode = True
        argv.remove('-s')
    if '--simple' in argv:
        simple_mode = True
        argv.remove('--simple')

    if argv:
        await io.error("!! rooms: command takes no arguments other than -s/--simple.")
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
            local_active_user_count = len(io.os.users.contexts) # All local users are in the active room

    room_data = []

    # 1. Gather data for all rooms
    for name in room_names:
        topic_path = f'/var/room/{name}/topic'
        topic_content = None # Initialize to None

        # Check if the topic file exists before attempting to get its content
        if await io.os.exists(io, topic_path):
            topic_content = await io.os.get(io, topic_path)
            # io.os.get will return None if it's not a file or is binary,
            # which is still handled correctly by the next line.

        topic = topic_content.strip() if topic_content else '(none)'

        is_active = (name == active_room_name)
        current_room_user_count = local_active_user_count if is_active else 0

        room_data.append({
            'name': name,
            'topic': topic,
            'users': current_room_user_count,
            'is_active': is_active
        })

    if simple_mode:
        # New simple (old non-verbose) output
        for data in room_data:
            display_name = data['name']
            if data['is_active']:
                # The prompt specifies ~roomname(user_count) for active rooms in simple mode too.
                display_name = f"~{display_name}({data['users']})" 
            await io.print(display_name)
    else:
        # New default (old verbose) output
        # 2. Calculate dynamic column widths
        max_room_len = len("ROOM")
        max_topic_len = len("TOPIC")

        for data in room_data:
            display_name = data['name']
            if data['is_active']:
                display_name = f"~{display_name}({data['users']})" # Includes count in name for active room
            
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
                display_name = f"~{display_name}({data['users']})" 
            
            await io.print(f"{display_name:<{max_room_len}}  {data['topic']:<{max_topic_len}}")
    
    # Final count
    count = len(room_names)
    # Add a newline before the final count for better spacing in default (verbose) mode
    if not simple_mode:
        await io.print("") 
        await io.print(f":: {count} room{'s' if count != 1 else ''} found.")

    return True

