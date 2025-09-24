async def iocall(io, argv):
    """Remove a file.

    Usage: rm <filename>
           rm --help

    <filename>: The name of the file to remove.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not argv:
        await io.error('!! rm: filename required')
        return

    filename = argv[0]

    if not await io.os.remove(io, filename):
        await io.error(f'!! rm: cannot remove file: {filename}')
        return

    await io.print(':: file removed')
    return True

