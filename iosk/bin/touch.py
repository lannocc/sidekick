async def iocall(io, args):
    if await io.os.create(io, args):
        await io.print(':: file created')
    else:
        await io.print(':: path exists')


