# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from os.path import join


async def iocall(io, args):
    if not io.os.chat:
        await io.error('!! no chat')
        return

    handle = args
    io.os.chat.join(handle, join('/dev', handle))
    return True

