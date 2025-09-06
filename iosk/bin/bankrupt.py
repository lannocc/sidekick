async def iocall(io, args):
    count = len(io.banks)
    if not count:
        await io.print(':: all banks clear')
        return

    io.banks = { }
    await io.print(f':: cleared {count} bank{"s" if count>1 else ""}')

