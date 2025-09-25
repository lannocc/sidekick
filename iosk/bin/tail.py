async def iocall(io, argv):
    """Display the last N lines of a file.

    Usage: tail [-n <number>] <filename>
           tail --help

    -n <number>:  Specifies the number of lines to display. Defaults to 10.
    <filename>:  The name of the file to read.
    --help: Displays this help message.
    """
    n = 10  # Default number of lines to show
    filename = None

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    arg_idx = 0

    if len(argv) > arg_idx and argv[arg_idx].startswith('-n'):
        opt = argv[arg_idx]
        if len(opt) > 2: # Case: -n3
            try:
                n = int(opt[2:])
            except ValueError:
                await io.error('!! tail: invalid number of lines for -n option')
                return
            arg_idx += 1
        else: # Case: -n <number>
            arg_idx += 1
            if len(argv) <= arg_idx:
                await io.error('!! tail: -n option requires a number')
                return
            try:
                n = int(argv[arg_idx])
            except ValueError:
                await io.error('!! tail: invalid number of lines for -n option')
                return
            arg_idx += 1

    if len(argv) > arg_idx:
        filename = argv[arg_idx]
    else:
        await io.error('!! tail: filename required')
        return

    if filename is None:
        await io.error('!! tail: filename required')
        return

    try:
        content = await io.os.get(io, filename)
        if content is None:  # get already handles the error message
            return

        lines = content.splitlines()
        start_index = max(0, len(lines) - n)
        for i in range(start_index, len(lines)):
            await io.print(lines[i])

        return True

    except Exception as e:
        await io.error(f'!! tail: error reading {filename}: {e}')

