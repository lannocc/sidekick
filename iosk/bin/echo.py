async def iocall(io, argv):
    """Echo the given arguments.

    Usage: echo [arguments]
           echo --help

    [arguments]: The text to display.
    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    # With the new parser in kernel.py, argv is already a list of tokens,
    # and variable expansion is handled by the kernel.
    # We just need to join them and print.
    if argv:
        await io.print(' '.join(argv))
    return True
