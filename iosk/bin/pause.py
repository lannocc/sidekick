from datetime import datetime # Added import

async def iocall(io, argv):
    """Pause a bot user's AI engagement.

    Usage: pause [username]
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

    target_user = argv[0] if argv else io.user

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

    confirmation_message = f":: user '{target_user}' has been paused at {current_time}."
    await io.print(confirmation_message)

    # If another user is pausing the target, inform the target user.
    if io.user != target_user:
        await target_io.print(confirmation_message)

    await io.os.system.print(f":: {io.user} paused user '{target_user}'")

    return True

