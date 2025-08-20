# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import aioconsole


async def iosend(io, data):
    #print(data)
    await aioconsole.aprint(data)


async def iorecv(io):
    return await aioconsole.ainput()

