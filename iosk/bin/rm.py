# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


async def iocall(io, args):
    args = args.split(' ')
    if len(args) != 1:
        await io.error(f'!! need 1 argument for remove: <path>')
        return

    await io.os.remove(io, args[0])

