#!/bin/skrip

async def iocall(io, args):
    """Execute a command as another user.

    Usage: su <user> <command> [args]
           su --help

    <user>: The username to switch to.
    <command>: The command to execute.
    [args]: Arguments for the command.
    --help: Displays this help message.
    """
    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not io.su:
        await io.error('!! must be super-user to su')
        return

    try: space = args.index(' ')
    except ValueError:
        await io.error(
                f'!! su needs at least 2 arguments: <user> <command> [args]')
        return

    user = args[:space]
    args = args[space+1:]

    if user not in io.os.users:
        await io.error(f'!! user not logged in: {user}')
        return

    #suio = io.fork()
    #suio.user = user
    suio = io.os.users[user] #.fork()

    #if not await io.os.call(suio, args):
    #    await io.error(f'!! su command failed')
    #    return

    #return True
    return await io.os.call(suio, args)

