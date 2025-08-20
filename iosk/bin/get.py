# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

async def iocall(io, args):
    await io.print(await io.get(args))

