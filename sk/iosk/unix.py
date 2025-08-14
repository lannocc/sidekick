# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..__version__ import __version__
from ..util import print_flush as print
from .. import ai

import asyncio
from datetime import datetime
import os
from os.path import join, isdir, exists
import importlib, importlib.util
import sys


class IOSK_System:

    class Devices:
        def __init__(self, iosk):
            self.iosk = iosk

        async def gemini(self, data):
            #print('GEMINI') #FIXME
            return await ai.async_prompt_for_text(data)


    def __init__(self, root=None):
        self.started = None
        self.ready = asyncio.Condition()
        self.root = root
        self.chat = None
        self.dev = self.Devices(self)

    async def start(self):
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

        ok = await self.exec('/sbin/init')
        if not ok: return

        print(f'IOSK UNIX is ready.')

        #await asyncio.sleep(81)

    async def run(self):
        async with self.ready: self.ready.notify_all()
        await asyncio.Future() # run forever

    async def exec(self, path, args=None): # FIXME use the args
        file = self.box(path)
        if not exists(file):
            print(f'!! path not found: {path}')
            return

        with open(file, 'r') as file:
            shebang = file.readline().rstrip()

        if shebang and shebang.startswith('#!'):
            shebang = shebang[2:]

            if shebang.startswith('/bin/'): # HACK
                return await self.call(shebang[5:] + ' ' + path) # ugly

            else:
                print(f'!! bad shebang: {path}')
                return

        else:
            print(f'!! no shebang: {path}')
            return

    async def send(self, dev, data):
        assert dev.startswith('/dev/')
        dev = dev[5:]
        return await getattr(self.dev, dev)(data)

    async def call(self, args):
        #print(f'CALL:"{args}"')
        space = args.index(' ') if ' ' in args else len(args)
        cmd = args[:space]
        args = args[space+1:]

        path = self.box(join('/bin', cmd)) # HACK
        #fullpath = join(os.getcwd(), path)
        #modname = fullpath[:-3] if cmd.endswith('.py') else fullpath
        #modname = modname.replace(os.sep, '.')
        modname = f'iosk.bin.{cmd}'
        #print(f'IMPORT {modname} at {path}')

        py = None
        try:
            spec = importlib.util.spec_from_file_location(
                    modname, path if path.endswith('.py') else f'{path}.py')
            #print(f'SPEC: {spec}')
            mod = importlib.util.module_from_spec(spec)
            #print(f'MOD: {mod}')
            sys.modules[modname] = mod
            spec.loader.exec_module(mod)
            py = mod
            #print(f'PY1: {py}')
        except:
            py = None

        if not py:
            # original way
            py = None
            try: py = importlib.import_module(f'sk.{modname}')
            except ModuleNotFoundError: pass
            #print(f'PY2: {py}')

        if py:
            #print('  CALL PYTHON')
            try:
                return await py.iocall(self, args)
            except: # FIXME error logging
                print(f'!! error calling: {args}')
                return

        else:
            #print('  CALL FILE')
            return await self.exec(join('/bin', cmd), args) # HACK

    def box(self, file): # sandbox
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

        return join(self.root, file)

