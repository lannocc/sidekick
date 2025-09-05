async def iocall(io, args):
    parents = False
    if args.startswith('-p '):
        parents = True
        args = args[3:]

    if await io.os.create_dir(io, args, parents):
        await io.os.print(':: directory created')

