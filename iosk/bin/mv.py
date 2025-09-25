async def iocall(io, argv):
    """Move or rename a file or directory.

    Usage: mv <source> <destination>
           mv --help

    <source>:  The source file or directory to move.
    <destination>:  The destination file or directory.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if len(argv) != 2:
        await io.error('!! mv needs 2 arguments: <source> <destination>')
        return

    source = argv[0]
    destination = argv[1]

    try:
        success = await io.os.move(io, source, destination)
        if not success:
            await io.error('!! mv: move failed')
            return
    except Exception as e:
        await io.error(f'!! mv: move failed: {e}')
        return

    await io.print(':: path moved')
    return
