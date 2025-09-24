async def iocall(io, args):
    """Manage IOSK command aliases.

    Usage: alias
           alias NAME=VALUE
           alias --help

    alias: List all currently defined aliases.
    NAME=VALUE: Define a new alias or update an existing one. NAME is the alias, VALUE is the command it expands to.
    --help: Displays this help message.
    """
    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    # Initialize io.aliases if it doesn't exist for the current session/context
    if not hasattr(io, 'aliases'):
        io.aliases = {}

    if not args:
        # List aliases
        if io.aliases:
            for name, value in io.aliases.items():
                await io.print(f"{name}='{value}'")
        else:
            await io.print("No aliases defined.")
    elif '=' in args:
        # Define an alias
        name, value = args.split('=', 1)
        if name: # Ensure name is not empty
            # Strip quotes from the value
            value = value.strip("'").strip('"')
            io.aliases[name] = value
            await io.print(f"Alias '{name}' defined as '{value}'")
        else:
            await io.print("Invalid alias definition. NAME cannot be empty. Use: alias NAME=VALUE")
    else:
        await io.print("Invalid usage. Use 'alias --help' for more information or 'alias NAME=VALUE' to define.")

    return True
