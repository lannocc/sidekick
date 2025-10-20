# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .cmd import main

import sys


def run():
    try:
        main(sys.argv[1:])

    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == '__main__':
    run()

