# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


class Context:
    def __init__(self, iosk_unix):
        self.os = iosk_unix # running system
        self.parent = None

    def fork(self):
        child = Context(self.os)
        child.parent = self
        return child

    async def print(self, args):
        print(args) # FIXME

    async def input(self, args):
        print(args) # FIXME

    async def output(self, args):
        print(args) # FIXME

    async def error(self, args):
        print(args) # FIXME

