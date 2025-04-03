# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .cmd import main

import sys


def run():
    try:
        main(sys.argv[1:], called=sys.argv[0])

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    run()

