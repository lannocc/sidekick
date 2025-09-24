async def iocall(io, args):
    """Create a directory.

    Usage: mkdir <directory>
           mkdir --help

    -p: allows parent directories to be created.
    <directory>: The name of the directory to create.
    --help: Displays this help message.
    """
    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not args:
        await io.error('!! mkdir: directory name required')
        return

    parents = False
    if args.startswith('-p '):
        parents = True
        args = args[3:]

    try:
        if await io.os.exists(io, args):
            await io.error(f'!! mkdir: path already exists: {args}')
            return

        success = await io.os.create_dir(io, args, parents)
        if not success:
            await io.error(f'!! mkdir: cannot create directory: {args}')
            return

    except Exception as e:
        await io.error(f'!! mkdir: failed to create directory {args}: {e}')
        return

    await io.print(':: directory created')
    return True
