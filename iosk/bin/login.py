import asyncio

DOCSTRING = """Log in as a different user.

Usage: login <username>
       login --help

Logs out the current session and starts a new session for the specified
user on the same device. This is useful for switching users without
restarting the system.
"""

async def iocall(io, argv):
    """
    Handles the 'login' command execution by logging out the current user
    and starting a new interactive session for the target user.
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

    await io.print(f":: Switching from {current_user} to {new_username}...")
    
    # Capture references before the current context is destroyed.
    os_ref = io.os
    
    # Perform logout. This removes the current user from the kernel's active user list.
    # The asyncio task for the current user's interactive session will be orphaned,
    # but the new interactive session will take over the console device.
    await os_ref.logout(io)
    
    # Perform login for the new user. 
    # The `interactive=True` flag is critical, as it starts a new blocking
    # command loop for the new user on the same device. This command will
    # not return until the new user's session ends (e.g., they 'exit' or 'login' again).
    await os_ref.login(user=new_username, device=current_device, interactive=True)
    
    # This part of the code will only be reached after the new user's session,
    # which was started by this command, has ended. The original user's session
    # is long gone, so we simply return.
    return True

