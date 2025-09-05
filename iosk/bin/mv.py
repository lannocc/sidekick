async def iocall(io, args):
    args = args.split(' ')
    if len(args) != 2:
        await io.error(f'!! mv needs 2 arguments: <src> <dst>')
        return

    if await io.os.move(io, args[0], args[1]):
        await io.print(':: path moved')

