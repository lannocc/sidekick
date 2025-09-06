async def iocall(io, args):
    """Remove a directory.

    Usage: rmdir <directory>
           rmdir --help

    <directory>: The name of the directory to remove.
    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not args:
        await io.error('!! rmdir: directory name required')
        return

    if not await io.os.remove_dir(io, args):
        await io.error(f'!! rmdir: cannot remove directory: {args}')
        return

    await io.print(':: directory removed')
    return True
