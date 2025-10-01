import shlex

async def iocall(io, argv):
    """Execute a command as another user, with optional piped input.

    Usage: su <user> <command> [args...]
           ... | su <user> <command> [args...]
           su --help

    <user>: The username to switch to.
    <command>: The command to execute.
    [args...]: Arguments for the command.
    --help: Displays this help message.

    When standard input is piped to `su`, it is passed as standard input
    to the executed command.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    #if not io.su:
    #    await io.error('!! must be super-user to su')
    #    return False

    if len(argv) < 2:
        await io.error(
                f'!! su needs at least 2 arguments: <user> <command> [args...]')
        return False

    user = argv[0]
    command_for_suio = argv[1:]

    if user not in io.os.users:
        await io.error(f'!! user not logged in: {user}')
        return False

    suio = io.os.users[user]

    # Pass the standard input from the current context (`io`)
    # to the target user's context (`suio`). The kernel's `call`
    # method will then use `suio.stdin` for the executed command.
    if hasattr(io, 'stdin') and io.stdin:
        suio.stdin = io.stdin

    command_string_for_suio = shlex.join(command_for_suio)

    return await io.os.call(suio, command_string_for_suio)

