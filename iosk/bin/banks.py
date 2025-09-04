# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


async def iocall(io, args):
    #if not io.banks:
    #    await io.print('no banks are loaded')
    #    return

    for bank in io.banks:
        await io.print(bank)

