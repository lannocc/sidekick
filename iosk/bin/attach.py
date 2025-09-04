# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from os.path import join


async def iocall(io, args):
    if args:
        args = args.split(' ')

    if len(args) < 1 or len(args) > 2:
        await io.error('!! 1-2 arguments required: <device> [handle]')
        return

    device = args[0]
    handle = args[1] if len(args) > 1 else device

    if not io.os.chat:
        await io.error('!! no chat')
        return

    io = await io.os.chat.join(handle, join('/dev', device))
    return True if io else False

