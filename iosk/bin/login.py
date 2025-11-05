import asyncio
import sys
import os

DOCSTRING = """Log in as a different user, creating a nested session.

Usage: login <username>
       login --help

Starts a new interactive session for the specified user on the same device.
The current session is suspended until the new user logs out by typing
'exit' or pressing Ctrl+D, at which point the original session resumes.
"""

async def iocall(io, argv):
    """
    Handles the 'login' command execution by creating a new, nested
    interactive session for the target user.
    """
    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if len(argv) != 1:
        await io.error("!! login: requires exactly one argument: <username>")
        return False

    new_username = argv[0]
    current_user = io.user
    current_device = io.dev

    if new_username == current_user:
        await io.print(":: You are already logged in as that user.")
        return True

    if new_username in io.os.users:
        await io.error(f"!! login: user '{new_username}' is already logged in.")
        return False

    await io.print(f":: Suspending session for {current_user}, starting session for {new_username}...")

    os_ref = io.os

    # Perform login for the new user to get their context (io object).
    new_io = await os_ref.login(user=new_username, device=current_device, interactive=False)

    if not new_io:
        # The login failed; os.login would have printed an error.
        await io.print(f":: Resuming session for {current_user}.")
        return False

    # Start the interactive loop for the new user. This call will block
    # until the new user logs out and will return the reason for exit.
    exit_reason = await os_ref.interactive(new_io)

    # After the nested session ends, if it was due to an EOF (Ctrl+D),
    # the underlying sys.stdin file descriptor is closed. We must reset it
    # for the parent session to be able to read from the console again.
    if exit_reason == 'eof' and sys.platform != "win32":
        try:
            sys.stdin.close()
            sys.stdin = open('/dev/tty')
        except (OSError, ValueError) as e:
            # This is a critical failure for an interactive session.
            # We can't recover input, so we should halt the system.
            await io.error(f"!! fatal: could not re-attach terminal ({e}).")
            await io.error("!! initiating system shutdown.")
            io.os.halt.set()
            return False # Exit the login command with failure

    # After the new session ends, control returns here. We print a resume message.
    await io.print(f"\n:: Session for {new_username} ended. Resuming session for {current_user}.")

    # The iocall returns, and the original user's interactive loop continues.
    return True

