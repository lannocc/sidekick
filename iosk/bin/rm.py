async def iocall(io, args):
    args = args.split(' ')
    if len(args) != 1:
        await io.error(f'!! need 1 argument for remove: <path>')
        return

    if await io.os.remove(io, args[0]):
        await io.print(':: file removed')

