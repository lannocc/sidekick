# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from datetime import date
from os import makedirs
from os.path import join, isdir, exists


class Context:
    def __init__(self, iosk_unix, dev_path='/dev/console', log_file=None):
        self.os = iosk_unix # running system
        self.dev = dev_path # device name path
        self.log = log_file # opened file handle
        self.parent = None  # parent Context

    def fork(self):
        child = Context(self.os, self.dev, self.log)
        child.parent = self
        return child

    async def print(self, args):
        #print(args) # FIXME
        if self.log:
            self.log.write(args)
            self.log.write('\n')

        await self.output(args)
        await self.output('\n')

    async def input(self):
        #print(args) # FIXME
        data = await self.os.recv(self, self.dev)
        return data

    async def output(self, args):
        if self.log:
            self.log.write(args)

        await self.os.send(self, self.dev, args)

    async def error(self, args):
        #print(args) # FIXME
        await self.print(args)
        # FIXME do more


class Capture:
    logs = { } # opened file handles keyed by path

    @classmethod
    def log(cls, iosk, path, mkdirs=False):
        if mkdirs:
            folder = iosk.box(path)
            if not exists(folder):
                makedirs(folder)

            elif not isdir(folder):
                raise ValueError(f'path exists but not a folder: {folder}')

        today = date.today().strftime('%Y-%m-%d')
        file_path = iosk.box(join(path, f'{today}.log'))

        if file_path in cls.logs:
            return cls.logs[file_path]

        else:
            file = open(file_path, 'a')
            cls.logs[file_path] = file
            return file

