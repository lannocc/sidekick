async def iocall(io, args):
    #if not io.session.banks:
    #    await io.print(':: no banks are loaded')
    #    return

    for bank in io.session.banks:
        await io.print(bank)

    count = len(io.session.banks)
    await io.print(f':: {count} bank{"s" if count != 1 else ""} loaded')