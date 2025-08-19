# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from sk.util import get_directory_tree_as_text


def iocall(iosk, args):
    print(get_directory_tree_as_text(iosk.box(args)))

