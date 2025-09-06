async def iocall(io, args):
    """Copy a file or directory.

    Usage: cp <source> <destination>
           cp --help

    <source>:  The source file or directory to copy.
    <destination>:  The destination file or directory.
    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    args = args.split(' ')
    if len(args) != 2:
        await io.error('!! cp needs 2 arguments: <source> <destination>')
        return

    source = args[0]
    destination = args[1]

    if await io.os.copy(io, source, destination):
        await io.print(':: path copied')
        return True

    else:
        await io.error('!! cp: copy failed')

