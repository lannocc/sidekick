async def iocall(io, argv):
    """Opens a new local chat room.

    Usage: room [room_name]
           room --help

    Opens a new chat room on the local system with the specified name.
    If no room_name is provided, it defaults to 'iosk'.

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

    # Determine room name from arguments. Defaults to 'iosk'.
    room_name = 'iosk'
    if not argv:
        # No arguments, use the default 'iosk'.
        pass
    elif len(argv) == 1:
        # One argument, use it as the room name.
        room_name = argv[0]
    else:
        # More than one argument is an error.
        await io.error("!! room: too many arguments. Use 'room --help' for usage.")
        return False

    # The open_room method in the chat subsystem handles all logic
    # and user feedback for opening a room.
    return await chat_subsystem.open_room(io, room_name)
