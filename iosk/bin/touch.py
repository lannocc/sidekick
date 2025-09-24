async def iocall(io, argv):
    """Create an empty file.

    Usage: touch <filename>
           touch --help

    <filename>: The name of the file to create.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not argv:
        await io.error('!! touch: filename required')
        return

    filename = argv[0]

    #if await io.os.exists(io, filename):
    #    # FIXME update timestamp
    #    return True

    if not await io.os.create(io, filename):
        await io.error(f'!! touch: cannot create file: {filename}')
        return

    await io.print(':: file created')
    return True
