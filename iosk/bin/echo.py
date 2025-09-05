from os.path import join

async def iocall(io, args):
    await io.print(f'{args}')
    return True

