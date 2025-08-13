# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from os.path import join


async def iocall(iosk, args):
    handle = args
    iosk.chat.join(handle, join('/dev', handle))
    return True

