import shlex # Added import for shlex

async def iocall(io, argv): # Changed 'args' to 'argv'
    """Execute a command as another user.

    Usage: su <user> <command> [args]
           su --help

    <user>: The username to switch to.
    <command>: The command to execute.
    [args]: Arguments for the command.
    --help: Displays this help message.
    """
    if '--help' in argv: # Updated check for '--help' in argv
        await io.print(iocall.__doc__)
        return

    if not io.su:
        await io.error('!! must be super-user to su')
        return

    # Changed argument parsing to use argv list directly
    if len(argv) < 2:
        await io.error(
                f'!! su needs at least 2 arguments: <user> <command> [args]')
        return

    user = argv[0] # Get user from the first argument
    # The rest of the arguments form the command to be executed by the target user
    command_for_suio = argv[1:]

    if user not in io.os.users:
        await io.error(f'!! user not logged in: {user}')
        return

    suio = io.os.users[user]

    # Reconstruct the command string for io.os.call, as it expects a string
    command_string_for_suio = shlex.join(command_for_suio)

    return await io.os.call(suio, command_string_for_suio)

