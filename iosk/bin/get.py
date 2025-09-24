async def iocall(io, argv):
    """Get the contents of a file.

    Usage: get <filename>
           get --help

    <filename>:  The name of the file to read.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if not argv:
        await io.error('!! get: filename required')
        return

    filename = argv[0]
    try:
        content = await io.os.get(io, filename)
        if content is None:
            return

        await io.print(content)
        return True

    except Exception as e:
        await io.error(f'!! get: error reading {filename}: {e}')
