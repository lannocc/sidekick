async def iocall(io, args):
    """Create an empty file.

    Usage: touch <filename>
           touch --help

    <filename>: The name of the file to create.
    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not args:
        await io.error('!! touch: filename required')
        return

    #if await io.os.exists(io, args):
    #    # FIXME update timestamp
    #    return True

    if not await io.os.create(io, args):
        await io.error(f'!! touch: cannot create file: {args}')
        return

    await io.print(':: file created')
    return True

