async def iocall(io, argv):
    """Count lines, words, and characters in a file or stdin.

    Usage: wc [file]
           wc --help

    If no file is specified, reads from standard input.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    content = None
    filename = ''

    if argv:
        filename = argv[0]
        content = await io.os.get(io, filename)
        if content is None:
            return False # Error already printed by get
    elif hasattr(io, 'stdin') and io.stdin:
        content = io.stdin.read()
    else:
        await io.error("!! wc: missing file operand and no piped input")
        return False

    if not content.strip():
        lines, words, chars = 0, 0, 0
    else:
        lines = content.count('\n')
        words = len(content.split())
        chars = len(content)

    await io.print(f"{lines}\t{words}\t{chars}\t{filename}")
    return True

