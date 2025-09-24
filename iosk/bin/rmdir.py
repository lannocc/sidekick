async def iocall(io, argv):
    """Remove a directory.

    Usage: rmdir <directory>
           rmdir --help

    <directory>: The name of the directory to remove.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not argv:
        await io.error('!! rmdir: directory name required')
        return

    directory_name = argv[0]

    if not await io.os.remove_dir(io, directory_name):
        await io.error(f'!! rmdir: cannot remove directory: {directory_name}')
        return

    await io.print(':: directory removed')
    return True
