async def iocall(io, args):
    """Get the contents of a file.

    Usage: get <filename>
           get --help

    <filename>:  The name of the file to read.
    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if not args:
        await io.error('!! get: filename required')
        return

    try:
        content = await io.os.get(io, args)
        if content is None:
            return

        await io.print(content)
        return True

    except Exception as e:
        await io.error(f'!! get: error reading {args}: {e}')
