# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..__version__ import __version__
from ..util import print_flush as print
from .. import ai

import asyncio
from datetime import datetime
import os
from os.path import join, isdir


class IOSK_System:
    def __init__(self, root=None):
        self.started = None
        self.ready = asyncio.Condition()
        self.root = root
        self.chat = None
        self.dev = self.Devices(self)

    async def run(self):
        print(f'IOSK UNIX is starting...')
        self.started = datetime.now()
        fail = None

        if not self.root:
            print('root: ', end='')
            self.root = input()

        if not self.root:
            fail = 'no root'

        elif not isdir(self.root):
            fail = 'bad root'

        '''
        elif not self.chat:
            fail = 'no chat'
        '''

        if fail:
            print(f'!! {fail}')
            self.started = None
            async with self.ready: self.ready.notify_all()
            return

        #await asyncio.sleep(9)

        await self.exec('/sbin/init')

        print(f'IOSK UNIX is ready.')
        async with self.ready: self.ready.notify_all()

        #await asyncio.sleep(81)
        await asyncio.Future() # run forever

    async def exec(self, path):
        file = box(self.root, path)
        with open(file, 'r') as file:
            shebang = file.readline().rstrip()

        if shebang and shebang.startswith('#!'):
            shebang = shebang[2:]

            if shebang == '/bin/skrip': # HACK
                await self.skrip(path)

            else:
                raise ValueError(f'unsupported shebang: {shebang}')

    async def skrip(self, path):
        file = box(self.root, path)
        with open(file, 'r') as file:
            for line in file:
                line = line.rstrip()
                if not line: continue

                if line.startswith('#'): # comment
                    continue

                elif line.startswith('$ '): # command
                    await self.call(line[2:])

                else: # chat
                    await self.chat.chat(line)

    async def send(self, dev, data):
        assert dev.startswith('/dev/')
        dev = dev[5:]
        return await getattr(self.dev, dev)(data)

    async def call(self, args):
        #print(f'CALL: {args}')

        if args.startswith('connect '):
            handle = args[8:]
            self.chat.join(handle, join('/dev', handle))


    class Devices:
        def __init__(self, iosk):
            self.iosk = iosk

        async def gemini(self, data):
            #print('GEMINI') #FIXME
            return await ai.async_prompt_for_text(data)


def box(root, file):
    while file:
        if file.startswith('/'):
            file = file[1:]
            continue

        elif file.startswith('./'):
            file = file[2:]
            continue

        elif file.startswith('../'):
            file = file[3:]
            continue

        else:
            break

    return join(root, file)

