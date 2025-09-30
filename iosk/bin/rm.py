async def iocall(io, argv):
    """Remove files.

    Usage: rm <filename>...
           rm --help

    <filename>: The name(s) of the file(s) to remove.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not argv:
        await io.error('!! rm: filename(s) required')
        return

    overall_success = True  # Track if all removal operations were successful

    for filename in argv:
        if not await io.os.remove(io, filename):
            await io.error(f'!! rm: cannot remove file: {filename}')
            overall_success = False  # Mark overall command as failed if any file fails
        else:
            await io.print(f':: file removed: {filename}')

    return overall_success  # Return True if all files were removed, False otherwise
