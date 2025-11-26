async def iocall(io, argv):
    """Undelete files that were removed from the distribution.

    This restores files by removing their 'tombstone' marker, making the
    original version from the distribution visible again. It cannot restore
    files that were created and deleted solely within the workspace.

    Usage: unrm <filename>...
           unrm --help

    <filename>: The name(s) of the file(s) to restore.
    --help: Displays this help message.
    """
    if '--help' in argv or not argv:
        await io.print(iocall.__doc__)
        if not argv:
            await io.error('!! unrm: filename(s) required')
        return

    overall_success = True
    for filename in argv:
        if await io.os.unremove(io, filename):
            await io.print(f':: file restored: {filename}')
        else:
            # error message is printed by fs.unremove
            overall_success = False
    
    return overall_success