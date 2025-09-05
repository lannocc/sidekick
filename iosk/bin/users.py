async def iocall(io, args):
    await io.print(' '.join(io.os.users.keys()))
    count = len(io.os.users)
    await io.print(f':: {count} user{"s" if count != 1 else ""} online')

