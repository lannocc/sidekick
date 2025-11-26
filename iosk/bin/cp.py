async def iocall(io, argv):
    """Copy a file or directory.

    Usage: cp <source> <destination>
           cp --help

    <source>:  The source file or directory to copy.
    <destination>:  The destination file or directory.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if len(argv) != 2:
        await io.error('!! cp needs 2 arguments: <source> <destination>')
        return

    source = argv[0]
    destination = argv[1]

    if await io.os.copy(io, source, destination):
        await io.print(':: path copied')
        return True

    else:
        await io.error('!! cp: copy failed')