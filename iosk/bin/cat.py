async def iocall(io, argv):
    """Display the contents of a file.

    Usage: cat <filename>
           cat --help

    <filename>:  The name of the file to read.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not argv:
        await io.error('!! cat: filename required')
        return

    filename = argv[0]
    try:
        content = await io.os.get(io, filename)
        if content is None:
            return

        await io.print(content)
        return True

    except Exception as e:
        await io.error(f'!! cat: error reading {filename}: {e}')
