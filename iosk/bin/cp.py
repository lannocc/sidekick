async def iocall(io, args):
    args = args.split(' ')
    if len(args) != 2:
        await io.error(f'!! need 2 arguments for copy: <src> <dst>')
        return

    if await io.os.copy(io, args[0], args[1]):
        await io.print(':: file copied')

