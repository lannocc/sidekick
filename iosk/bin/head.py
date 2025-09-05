async def iocall(io, args):
    """Display the first N lines of a file.

    Usage: head [-n <number>] <filename>
           head --help

    -n <number>:  Specifies the number of lines to display. Defaults to 10.
    <filename>:  The name of the file to read.
    --help: Displays this help message.
    """
    args = args.split(' ')
    n = 10  # Default number of lines to show
    filename = None

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    try:
        if len(args) >= 1:
            if args[0].startswith('-n'):
                try:
                    if len(args[0]) > 2:
                        n = int(args[0][2:])  # Handle -n3 case
                        filename = args[1] if len(args) > 1 else None
                    else:
                        try:
                            n = int(args[1])
                            filename = args[2] if len(args) > 2 else None
                        except (ValueError, IndexError):
                            await io.error('!! head: invalid number of lines')
                            return
                except ValueError:
                    await io.error('!! head: invalid number of lines')
                    return
                if filename is None:
                    await io.error('!! head: filename required')
                    return
            else:
                filename = args[0]
        else:
            await io.error('!! head: filename required')
            return
    except IndexError:
        await io.error('!! head: missing operand')
        return

    if filename is None:
        await io.error('!! head: filename required')
        return

    try:
        content = await io.os.get(io, filename)
        if content is None:  # get already handles the error message
            return

        lines = content.splitlines()
        for i in range(min(n, len(lines))):
            await io.print(lines[i])

        return True

    except Exception as e:
        await io.error(f'!! head: error reading {filename}: {e}')

