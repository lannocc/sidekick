import os
from os.path import exists, isdir

async def iocall(io, args):
    return await io.os.call(io, f'ls -l {args}')

