from datetime import datetime # Added import
import shlex

async def iocall(io, argv):
    """Unpause a bot user's AI engagement.

    Usage: unpause <username[.host]>
           unpause --help

    Resumes the AI engagement for a previously paused bot user.
    This command must be run by another user, as a paused user cannot
    execute commands.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if len(argv) != 1:
        await io.error("!! unpause: requires exactly one argument: <username>")
        return False

    target_user = argv[0]

    if '.' in target_user:
        parts = target_user.rsplit('.', 1)
        if len(parts) == 2:
            potential_user, potential_host = parts
            
            is_remote_request = (
                io.os.port and
                potential_host != io.os.hostname and
                potential_host in io.os.port.routing_table
            )

            if is_remote_request:
                command_str = f"unpause {shlex.quote(potential_user)}"
                await io.print(f":: dispatching to {potential_host}: {command_str}")
                return await io.os.port.stream_remote_exec(potential_host, command_str, io)

            if potential_host == io.os.hostname:
                # It's explicitly for the local host, so strip the host part
                target_user = potential_user

    # --- Local Execution ---

    # Validation
    if target_user not in io.os.users:
        await io.error(f"!! unpause: user '{target_user}' not found.")
        return False

    target_io = io.os.users[target_user]

    if not target_io.bot:
        await io.error(f"!! unpause: user '{target_user}' is not a bot and cannot be unpaused.")
        return False

    if target_user not in io.os.chat.engagements:
        await io.error(f"!! unpause: no active engagement for bot user '{target_user}'.")
        return False

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Get current date and time

    if not target_io.paused:
        await io.print(f":: user '{target_user}' is not paused.")
        return True

    # Unpause the user by setting the flag on their context
    target_io.paused = False

    # Broadcast the state change to network peers
    if io.os.port:
        await io.os.port.broadcast_to_peers({
            'type': 'user_update',
            'action': 'state_update',
            'user': target_user,
            'host': io.os.hostname,
            'paused': False
        })

    # Broadcast the state change to local clients
    if io.os.chat:
        await io.os.chat._broadcast_room_state_update()

    confirmation_message = f":: user '{target_user}' has been unpaused at {current_time}."
    await io.print(confirmation_message)
    await target_io.print(confirmation_message)
    await io.os.system.print(f":: {io.user} unpaused user '{target_user}'")

    return True