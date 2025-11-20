async def iocall(io, argv):
    """Manage IOSK command aliases.

    Usage: alias
           alias NAME=VALUE
           alias --help

    alias: List all currently defined aliases.
    NAME=VALUE: Define a new alias or update an existing one. NAME is the alias, VALUE is the command it expands to.
    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    # io.session.aliases is guaranteed to exist for any active session.

    if not argv:
        # List aliases
        if io.session.aliases:
            for name, value in io.session.aliases.items():
                await io.print(f"{name}='{value}'")
        else:
            await io.print(":: No aliases defined.")
    elif len(argv) == 1 and '=' in argv[0]:
        # Define an alias
        name, value = argv[0].split('=', 1)
        if name: # Ensure name is not empty
            # Strip quotes from the value
            value = value.strip("'").strip('"')
            io.session.aliases[name] = value
            await io.print(f":: Alias '{name}' defined as '{value}'")
        else:
            await io.error("!! Invalid alias definition. NAME cannot be empty. Use: alias NAME=VALUE")
    else:
        await io.error("!! Invalid usage. Use 'alias --help' for more information or 'alias NAME=VALUE' to define.")

    return True

