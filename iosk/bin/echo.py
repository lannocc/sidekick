async def iocall(io, args):
    """Echo the given arguments.

    Usage: echo [arguments]
           echo --help

    [arguments]: The text to display.
    --help: Displays this help message.
    """
    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    if args:
        # variable substitution (hack until proper shell support)
        env = io.environ()
        while '$' in args:
            i = args.index('$')
            try: s = args.index(' ', i)
            except ValueError: s = len(args)
            name = args[i+1:s]
            val = env[name] if name in env else ''
            args = args[:i] + val + args[s:]

        await io.print(args)
    return True
