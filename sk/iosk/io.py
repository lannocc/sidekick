# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


class Context:
    def __init__(self, iosk_unix, dev_name='/dev/console'):
        self.os = iosk_unix # running system
        self.dev = dev_name # device name
        self.parent = None

    def fork(self):
        child = Context(self.os)
        child.parent = self
        return child

    async def print(self, args):
        #print(args) # FIXME
        await self.output(args)
        await self.output('\n')

    async def input(self):
        #print(args) # FIXME
        return await self.os.recv(self, self.dev)

    async def output(self, args):
        await self.os.send(self, self.dev, args)

    async def error(self, args):
        #print(args) # FIXME
        await self.print(args)
        # FIXME do more

