async def iocall(io, args):
    """List loaded memory banks.

    Usage: banks
           banks -h | --help

    Lists the names (keys) of all memory banks currently loaded
    in the user's session, followed by a total count.
    """
    if '-h' in args or '--help' in args:
        await io.print(iocall.__doc__)
        return True

    #if not io.session.banks:
    #    await io.print(':: no banks are loaded')
    #    return

    for bank in io.session.banks:
        await io.print(bank)

    count = len(io.session.banks)
    await io.print(f':: {count} bank{"s" if count != 1 else ""} loaded')
    return True

