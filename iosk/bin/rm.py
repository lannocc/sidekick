async def iocall(io, args):
    """Remove a file.

    Usage: rm <filename>
           rm --help

    <filename>: The name of the file to remove.
    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not args:
        await io.error('!! rm: filename required')
        return

    if not await io.os.remove(io, args):
        await io.error(f'!! rm: cannot remove file: {args}')
        return

    await io.print(':: file removed')
    return True

