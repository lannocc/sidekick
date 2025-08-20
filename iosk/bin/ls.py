# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from sk.util import get_directory_tree_as_text


async def iocall(io, args):
    await io.print(get_directory_tree_as_text(io.os.box(args)))

