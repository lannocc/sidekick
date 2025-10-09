async def iocall(io, argv):
    """Creates or displays the status of the local chat room.

    Usage: room
           room <room_name>
           room --help

    room:
      If a room is active, displays its name and topic. Otherwise,
      indicates no room is active.

    room <room_name>:
      Opens a new chat room on the local system with the specified name.
      Only one room can be active at a time. This command will fail if
      a room is already open.

    --help:
      Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__.strip())
        return True

    chat_subsystem = io.os.chat
    if not chat_subsystem:
        await io.error("!! room: chat subsystem is not available.")
        return False

    # Case 1: 'room' (status check)
    if not argv:
        if chat_subsystem.active_room:
            await io.print(f":: Current room: {chat_subsystem.active_room}")
            topic = chat_subsystem.room_topic or "(not set)"
            await io.print(f":: Topic: {topic}")
        else:
            await io.print(":: No room is currently active.")
        return True

    # Case 2: 'room <room_name>'
    if len(argv) == 1:
        room_name = argv[0]
        # The open_room method in the chat subsystem handles all logic
        # and user feedback for opening a room.
        return await chat_subsystem.open_room(io, room_name)

    # Case 3: Too many arguments
    await io.error("!! room: too many arguments. Use 'room --help' for usage.")
    return False
