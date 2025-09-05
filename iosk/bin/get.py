async def iocall(io, args):
    data = await io.os.get(io, args)
    if data is None: return
    await io.output(data)

