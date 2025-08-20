# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context
from ..util import print_flush as print

import asyncio
from datetime import datetime
import os
from os.path import join, isdir, exists
import importlib, importlib.util
import sys


class IOSK_System:
    def __init__(self, root=None):
        self.started = None
        self.ready = asyncio.Condition()
        self.root = root
        self.chat = None

    ###
    ### PROCESS
    ###

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

        ok = await self.exec('/sbin/init')
        if not ok: return

        print(f'IOSK UNIX is ready.')
        #await asyncio.sleep(81)

    async def run(self):
        async with self.ready: self.ready.notify_all()
        await asyncio.Future() # run forever

    ###
    ### FILE I/O
    ###

    async def get(self, path, io=None):
        """Get file contents."""
        io = io.fork() if io else Context(self)

        file = self.box(path)
        if not exists(file):
            await io.error(f'!! path not found: {path}')
            return

        with open(file, 'r', encoding='utf-8') as file:
            return file.read()

    async def exec(self, path:str, args:list[str]=None, io=None):
        """When you know what you need and you've come prepared (arguments)."""
        io = io.fork() if io else Context(self)

        file = self.box(path)
        if not exists(file):
            await io.error(f'!! path not found: {path}')
            return

        with open(file, 'r') as file:
            shebang = file.readline().rstrip()

        if shebang and shebang.startswith('#!'):
            shebang = shebang[2:]

            if shebang.startswith('/bin/'): # HACK
                args = ' ' + ' '.join(args) if args else ''
                # ugly:
                return await self.call(shebang[5:] + ' ' + path + args, io=io)

            else:
                await io.error(f'!! bad shebang: {path}')
                return

        else:
            await io.error(f'!! no shebang: {path}')
            # TODO support real binaries (executables), etc.
            return

    async def send(self, dev, data, io=None):
        """Send data to device."""
        io = io.fork() if io else Context(self)

        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return

        dev = dev[5:]
        #return await getattr(self.dev, dev)(data)
        path = self.box(join('/dev', dev))

        modname = f'iosk.dev.{dev}'
        py = self.pymod(modname, path)

        if py:
            #print('  SEND PYTHON')
            try:
                return await py.iosend(io, data)
            except Exception as e: # FIXME error logging
                await io.error(f'!! error sending: {data}')
                #return
                raise e

        else:
            print(f'  SEND FILE: {path}')
            #return await self.exec(join('/dev', dev), args)

    ###
    ### COMMAND
    ###

    async def call(self, args, io=None):
        """Interpret arguments for something to invoke (exec)."""
        #print(f'CALL:"{args}"')
        space = args.index(' ') if ' ' in args else len(args)
        cmd = args[:space]
        args = args[space+1:]

        path = self.box(join('/bin', cmd)) # HACK
        modname = f'iosk.bin.{cmd}'
        py = self.pymod(modname, path)

        if py:
            #print('  CALL PYTHON')
            io = io.fork() if io else Context(self)
            try:
                return await py.iocall(io, args)
            except: # FIXME error logging
                await io.error(f'!! error calling: {cmd} {args}')
                return

        else:
            #print('  CALL FILE')
            return await self.exec(join('/bin', cmd), args, io=io) # HACK

    ###
    ### UTILITY
    ###

    def box(self, file): # sandbox
        """Sandbox file path."""
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

    def pymod(self, modname, path):
        """Import python module at path as the given module name."""
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

        return py

