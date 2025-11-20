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
    if target_user not in io.os.users.contexts:
        await io.error(f"!! unpause: user '{target_user}' not found.")
        return False

    target_io = io.os.users.contexts[target_user]

    if not target_io.session.bot:
        await io.error(f"!! unpause: user '{target_user}' is not a bot and cannot be unpaused.")
        return False

    if target_user not in io.os.chat.engagements:
        await io.error(f"!! unpause: no active engagement for bot user '{target_user}'.")
        return False

    if not target_io.session.paused:
        await io.print(f":: user '{target_user}' is not paused.")
        return True

    # Use the new centralized method in UserManager to set the state and broadcast.
    return await io.os.users.set_user_pause_state(io, target_user, paused=False)