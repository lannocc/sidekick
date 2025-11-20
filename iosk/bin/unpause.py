from datetime import datetime # Added import
from sk.iosk.util import dispatch_remote_if_needed

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

    # Check for and handle remote dispatch
    dispatched, result = await dispatch_remote_if_needed(io, 'unpause', argv)
    if dispatched:
        return result
    argv = result  # Update argv with hostname stripped if necessary

    target_user = argv[0]

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
