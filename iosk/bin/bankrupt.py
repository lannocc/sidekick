async def iocall(io, args):
    count = len(io.session.banks)
    if not count:
        await io.print(':: all banks clear')
        return

    io.session.banks = { }
    await io.print(f':: cleared {count} bank{"s" if count>1 else ""}')

