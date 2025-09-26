async def iocall(io, argv):
    """Remove one or more directories.

    Usage: rmdir <directory>...
           rmdir --help

    <directory>: The name of a directory to remove.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True # Indicate successful display of help

    if not argv:
        await io.error('!! rmdir: directory name required')
        return False

    all_operations_successful = True

    for directory_name in argv:
        if not await io.os.remove_dir(io, directory_name):
            await io.error(f'!! rmdir: cannot remove directory: {directory_name}')
            all_operations_successful = False
        else:
            await io.print(f':: directory {directory_name} removed')

    return all_operations_successful
