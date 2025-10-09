async def iocall(io, argv):
    """View or set the topic for the current chat room.

    Usage: topic
           topic <new topic>
           topic --help

    topic:          Displays the current room's topic.
    <new topic>:    Sets the room's topic to the provided text.
                    Only the room owner or a superuser can set the topic.
    --help:         Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__.strip())
        return True

    chat_subsystem = io.os.chat
    if not chat_subsystem:
        await io.error("!! topic: chat subsystem is not available.")
        return False

    if not chat_subsystem.active_room:
        await io.error("!! topic: not in a room.")
        return False

    # Case 1: View topic
    if not argv:
        topic = chat_subsystem.room_topic
        if topic:
            await io.print(f":: Topic for '{chat_subsystem.active_room}': {topic}")
        else:
            await io.print(f":: No topic set for room '{chat_subsystem.active_room}'.")
        return True

    # Case 2: Set topic
    # Permission check
    if not io.su and io.user != chat_subsystem.room_owner:
        await io.error(f"!! topic: permission denied. Only the owner ('{chat_subsystem.room_owner}') or a superuser can set the topic.")
        return False

    new_topic = ' '.join(argv)
    
    # Update state in memory
    chat_subsystem.room_topic = new_topic

    # Persist the topic to the filesystem
    topic_file_virtual = f'/var/room/{chat_subsystem.active_room}/topic'
    topic_file_host = io.os.box(topic_file_virtual, io_context=io)
    try:
        # 'w' mode will create the file if it doesn't exist
        with open(topic_file_host, 'w', encoding='utf-8') as f:
            f.write(new_topic)
    except Exception as e:
        await io.error(f"!! topic: failed to write topic file: {e}")
        return False

    # Announce the change locally
    announcement = f":: {io.user} set the topic to: {new_topic}"
    await chat_subsystem.send(io.user, announcement, sys=True)

    # Announce the change to network peers
    if io.os.port:
        await io.os.port.broadcast_to_peers({
            'type': 'room_update',
            'action': 'topic_change',
            'name': chat_subsystem.active_room,
            'host': io.os.hostname,
            'topic': new_topic
        })
    
    return True
