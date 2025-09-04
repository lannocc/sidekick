# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


async def iocall(io, args):
    count = len(io.banks)
    if not count: return

    io.banks = { }
    await io.print(f'cleared {count} bank{"s" if count>1 else ""}')

