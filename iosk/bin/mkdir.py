async def iocall(io, argv):
    """Create a directory.

    Usage: mkdir <directory>...
           mkdir -p <directory>...
           mkdir --help

    -p: allows parent directories to be created.
    <directory>: The name of the directory to create. Multiple directories can be specified.
    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True # Indicate success for displaying help

    parents = False
    dir_name_start_index = 0

    # Parse options. For simplicity, we assume -p, if present, is the first argument.
    if argv and argv[0] == '-p':
        parents = True
        dir_name_start_index = 1

    # Get the list of actual directory names to create
    directories_to_create = argv[dir_name_start_index:]

    if not directories_to_create:
        # Check if -p was provided without any directory names
        if parents and dir_name_start_index > 0:
            await io.error('!! mkdir: directory name required after -p option')
        else: # No arguments at all, or only options without directories
            await io.error('!! mkdir: directory name required')
        return False # Indicate failure

    all_successful = True # Tracks if all creation attempts were successful

    for dirname in directories_to_create:
        try:
            # The io.os.create_dir method internally checks if the path exists
            # and prints an error message if it does. It is assumed to return
            # True on successful creation and False on failure (e.g., if already exists).
            success = await io.os.create_dir(io, dirname, parents)
            if not success:
                # If create_dir returns False, it implies a failure.
                # create_dir is expected to have already printed a specific error message.
                all_successful = False
                # Continue processing other directories even if one fails
        except Exception as e:
            # This catches exceptions during the call to create_dir itself
            await io.error(f'!! mkdir: failed to create directory {dirname}: {e}')
            all_successful = False
            # Continue processing other directories

    # Final reporting
    if all_successful:
        # If all calls to create_dir returned True, implies successful creation for all.
        await io.print(f':: director{"ies" if len(directories_to_create) > 1 else "y"} created')
        return True
    else:
        # If any operation failed (returned False or raised an exception),
        # specific error messages would have been printed in the loop.
        return False

