from datetime import datetime # Added import

async def iocall(io, argv):
    """Unpause a bot user's AI engagement.

    Usage: unpause <username>
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

    confirmation_message = f":: user '{target_user}' has been unpaused at {current_time}."
    await io.print(confirmation_message)
    await target_io.print(confirmation_message)
    await io.os.system.print(f":: {io.user} unpaused user '{target_user}'")

    return True

