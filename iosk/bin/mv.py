async def iocall(io, args):
    """Move or rename a file or directory.

    Usage: mv <source> <destination>
           mv --help

    <source>:  The source file or directory to move.
    <destination>:  The destination file or directory.
    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    args = args.split(' ')
    if len(args) != 2:
        await io.error('!! mv needs 2 arguments: <source> <destination>')
        return

    source = args[0]
    destination = args[1]

    if not await io.os.move(io, source, destination):
        await io.error('!! mv: move failed')
        return

    await io.print(':: path moved')
    return True

