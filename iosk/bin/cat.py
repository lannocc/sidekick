async def iocall(io, args):
    await io.print(await io.os.get(io, args))

