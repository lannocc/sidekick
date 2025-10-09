async def iocall(io, argv):
    """Close the active chat room.

    Usage: clroom
           clroom --help

    Closes the single active chat room on the local system. This command can
    typically only be run by the room's owner or a superuser.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__.strip())
        return True

    if argv:
        await io.error("!! clroom: command takes no arguments. Use 'clroom --help'.")
        return False

    chat_subsystem = io.os.chat
    if not chat_subsystem:
        await io.error("!! clroom: chat subsystem is not available.")
        return False

    # The close_room method in the chat subsystem handles all logic,
    # including permission checks and user feedback for success or failure.
    # We just need to call it and return its result.
    return await chat_subsystem.close_room(io)
