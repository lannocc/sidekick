# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


async def iocall(io, args):
    parents = False
    if args.startswith('-p '):
        parents = True
        args = args[3:]

    await io.os.create_dir(io, args, parents)

