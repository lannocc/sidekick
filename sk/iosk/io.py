# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from datetime import datetime, date
from os import makedirs
from os.path import join, isdir, exists


class Context:
    CID = 0 # next "chatter" id
    CHATTER = '/var/cache/chatter'

    def __init__(self, iosk_unix, dev_path, log_file=None):
        self.cid = Context.CID
        Context.CID += 1

        self.os = iosk_unix # running system
        self.dev = dev_path # device name path
        self.log = log_file # opened file handle
        self.parent = None  # parent Context

        chatter = join(self.CHATTER, str(self.os.BOOT), str(self.cid))
        self.chatter = open(self.os.box(chatter), 'w')

    def fork(self):
        child = Context(self.os, self.dev, self.log)
        child.parent = self
        return child

    async def print(self, args):
        if self.log:
            self._log_()
            #self.log.write('<< ')

        await self.output(args)
        await self.output('\n')

    async def input(self):
        if self.log:
            self._log_()
            self.log.write('>> ')

        data = await self.os.recv(self, self.dev)

        if self.log:
            self.log.write(data)
            self.log.write('\n')

        return data

    async def output(self, args):
        self.chatter.write(args)

        if self.log:
            self.log.write(args)

        await self.os.send(self, self.dev, args)

    async def error(self, args):
        await self.print(args)

    def _log_(self):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log.write(f'=== {now} [{self.os.BOOT}/{self.cid}] === ')


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

