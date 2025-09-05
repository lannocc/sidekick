async def iocall(io, args):
    if await io.os.remove_dir(io, args):
        await io.print(':: directory removed')

