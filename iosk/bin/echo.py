async def iocall(io, args):
    """Echo the given arguments.

    Usage: echo [arguments]
           echo --help

    [arguments]: The text to display.
    --help: Displays this help message.
    """
    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if args:
        await io.print(args)
    return True
