async def iocall(io, args):
    """Set or display environment variables.

    Usage: export [NAME=VALUE] ...
           export --help

    With no arguments, `export` prints a list of all environment variables.
    Otherwise, it sets each `NAME` to `VALUE`.
    """
    if args is None:
        args = ''

    tokens = args.split()

    if args.strip() == '--help' or '--help' in tokens:
        await io.print(iocall.__doc__)
        return True

    if not tokens:
        # No arguments, print all environment variables
        env = io.environ()
        if env:
            for key, value in sorted(env.items()):
                # Use repr() to get a safely quoted version of the value,
                # which is suitable for re-input into a shell.
                await io.print(f"{key}={repr(value)}")
        return True

    # Arguments are present, so we're setting variables.
    for token in tokens:
        if '=' not in token:
            await io.error(f"!! export: invalid argument: '{token}'. Use NAME=VALUE.")
            return False

        key, value = token.split('=', 1)

        if not key.isidentifier():
            await io.error(f"!! export: '{key}' is not a valid identifier.")
            return False

        # Strip a single layer of quotes from the value
        if len(value) >= 2 and (
            (value.startswith("'") and value.endswith("'")) or
            (value.startswith('"') and value.endswith('"'))
        ):
            value = value[1:-1]

        io.env[key] = value

    return True
