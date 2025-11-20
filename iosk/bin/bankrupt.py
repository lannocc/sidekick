async def iocall(io, args):
    """Clear all memory banks.

    Usage: bankrupt
           bankrupt -h | --help

    Removes all loaded memory banks from the current session.
    """
    if '-h' in args or '--help' in args:
        await io.print(iocall.__doc__)
        return True

    count = len(io.session.banks)
    if not count:
        await io.print(':: all banks clear')
        return True

    io.session.banks = { }
    await io.print(f':: cleared {count} bank{"s" if count>1 else ""}')
    return True

