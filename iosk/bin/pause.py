from datetime import datetime # Added import
from sk.iosk.util import dispatch_remote_if_needed

async def iocall(io, argv):
    """Pause a bot user's AI engagement.

    Usage: pause [username[.host]]
           pause --help

    Pauses the AI engagement for the specified bot user. The bot will stop
    making AI trips and will not receive new chat messages until unpaused.

    If no username is provided, this command attempts to pause the current user.
    The console user cannot be paused.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if len(argv) > 1:
        await io.error("!! pause: too many arguments.")
        return False

    # Check for and handle remote dispatch
    dispatched, result = await dispatch_remote_if_needed(io, 'pause', argv)
    if dispatched:
        return result
    argv = result  # Update argv with hostname stripped if necessary

    if argv:
        target_user = argv[0]
    else:
        target_user = io.user

    # --- Local Execution ---

    # Validation
    if target_user not in io.os.users:
        await io.error(f"!! pause: user '{target_user}' not found.")
        return False

    target_io = io.os.users[target_user]

    if not target_io.bot:
        await io.error(f"!! pause: cannot pause console user '{target_user}'.")
        return False

    if target_user not in io.os.chat.engagements:
        # This case should be rare if target_io.bot is true, but it's a good safeguard.
        await io.error(f"!! pause: no active engagement for bot user '{target_user}'.")
        return False

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Get current date and time

    if target_io.paused:
        await io.print(f":: user '{target_user}' is already paused.")
        return True

    # Pause the user by setting the flag on their context
    target_io.paused = True

    # Broadcast the state change to network peers
    if io.os.port:
        await io.os.port.broadcast_to_peers({
            'type': 'user_update',
            'action': 'state_update',
            'user': target_user,
            'host': io.os.hostname,
            'paused': True
        })

    # Broadcast the state change to local clients
    if io.os.chat:
        await io.os.chat._broadcast_room_state_update()

    confirmation_message = f":: user '{target_user}' has been paused at {current_time}."
    await io.print(confirmation_message)

    # If another user is pausing the target, inform the target user.
    if io.user != target_user:
        await target_io.print(confirmation_message)

    await io.os.system.print(f":: {io.user} paused user '{target_user}'")

    return True
