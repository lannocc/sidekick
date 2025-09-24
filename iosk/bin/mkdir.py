async def iocall(io, argv):
    """Create a directory.

    Usage: mkdir <directory>
           mkdir --help

    -p: allows parent directories to be created.
    <directory>: The name of the directory to create.
    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not argv:
        await io.error('!! mkdir: directory name required')
        return

    parents = False
    dir_name_index = 0

    if argv[0] == '-p':
        parents = True
        dir_name_index = 1
        if len(argv) <= dir_name_index:
            await io.error('!! mkdir: directory name required after -p option')
            return

    dirname = argv[dir_name_index]

    try:
        # The io.os.create_dir method internally checks if the path exists
        # and prints an error message if it does. It is assumed to return
        # True on successful creation and False on failure (e.g., if already exists).
        success = await io.os.create_dir(io, dirname, parents)
        if not success:
            # If create_dir returns False, it implies a failure, and create_dir
            # is expected to have already printed a specific error message if applicable.
            # We add a generic error here as a fallback, but it should ideally
            # not be reached if create_dir provides specific feedback.
            await io.error(f'!! mkdir: cannot create directory: {dirname}')
            return

    except Exception as e:
        await io.error(f'!! mkdir: failed to create directory {dirname}: {e}')
        return

    await io.print(':: directory created')
    return True

