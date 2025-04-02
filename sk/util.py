# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from sys import stdout


def print_flush(*args, **kwargs):
    print(*args, **kwargs)
    stdout.flush()

