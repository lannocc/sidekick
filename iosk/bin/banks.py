async def iocall(io, args):
    #if not io.banks:
    #    await io.print(':: no banks are loaded')
    #    return

    for bank in io.banks:
        await io.print(bank)

    count = len(io.banks)
    await io.print(f':: {count} bank{"s" if count != 1 else ""} loaded')

