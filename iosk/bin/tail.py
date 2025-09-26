async def iocall(io, argv):
    """Display the last N lines of a file or stdin.

    Usage: tail [-n <number>] [filename]
           tail --help

    -n <number>:  Specifies the number of lines to display. Defaults to 10.
    [filename]:   The name of the file to read. If omitted, reads from stdin.
    --help: Displays this help message.
    """
    n = 10
    arg_idx = 0

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if len(argv) > arg_idx and argv[arg_idx].startswith('-n'):
        # ... (same -n parsing logic as before)
        opt = argv[arg_idx]
        if len(opt) > 2:
            try: n = int(opt[2:])
            except ValueError:
                await io.error('!! tail: invalid number for -n')
                return False
            arg_idx += 1
        else:
            arg_idx += 1
            if len(argv) <= arg_idx:
                await io.error('!! tail: -n option requires a number')
                return False
            try: n = int(argv[arg_idx])
            except ValueError:
                await io.error('!! tail: invalid number for -n')
                return False
            arg_idx += 1

    content = None
    if len(argv) > arg_idx:
        filename = argv[arg_idx]
        content = await io.os.get(io, filename)
        if content is None:
            return False
    elif hasattr(io, 'stdin') and io.stdin:
        content = io.stdin.read()
    else:
        await io.error('!! tail: requires a file or piped input')
        return False

    lines = content.splitlines()
    start_index = max(0, len(lines) - n)
    for i in range(start_index, len(lines)):
        await io.print(lines[i])

    return True

