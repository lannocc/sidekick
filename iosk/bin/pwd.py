# bin/pwd.py
async def iocall(io, argv):
    """Print the name of the current working directory.

    Usage: pwd
           pwd --help

    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if argv:
        await io.error("!! pwd: does not accept arguments. Use 'pwd --help' for usage.")
        return False

    await io.print(io.pwd)
    return True
