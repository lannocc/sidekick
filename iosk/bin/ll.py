import os
from os.path import exists, isdir

async def iocall(io, argv):
    return await io.os.call(io, f"ls -l {' '.join(argv)}")

