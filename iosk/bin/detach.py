# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from os.path import join


async def iocall(io, args):
    if not io.os.chat:
        await io.error('!! no chat')
        return

    handle = args
    if handle not in io.os.users:
        await io.error(f'!! not attached: {handle}')
        return

    await io.os.chat.leave(io.os.users[handle])
    return True

