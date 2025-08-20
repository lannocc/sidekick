# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context
from ..util import print_flush as print

import asyncio
import aioconsole
from datetime import datetime
import os
from os.path import join, isdir, exists
import importlib, importlib.util
import sys
import shutil


class IOSK_System:
    def __init__(self, root=None):
        self.started = None
        #self.ready = asyncio.Condition()
        self.ready = asyncio.Event()
        self.root = root
        self.chat = None
        self.halt = asyncio.Event()

    ###
    ### PROCESS
    ###

    async def start(self):
        print(f'IOSK UNIX is starting...')
        self.started = datetime.now()
        fail = None

        io = Context(self, '/dev/console')

        if not self.root:
            await io.print('root: ', end='')
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
            await io.error(f'!! {fail}')
            self.started = None
            #async with self.ready: self.ready.notify_all()
            self.ready.set()
            return

        ##- init -##
        ok = await self.exec(io, '/sbin/init')
        if not ok: return

        await io.print(f'IOSK UNIX is ready.')
        #await asyncio.sleep(81)

        return io

    async def run(self, io, interactive=False):
        #async with self.ready: self.ready.notify_all()
        self.ready.set()

        if interactive:
            #print(f'SHELL IO {io}')
            await self.shell(io, True)

        #await asyncio.Future() # run forever
        await self.halt.wait()

    async def shell(self, io, interactive=False):
        skrc = self.box('/etc/skrc')
        if exists(skrc):
            await self.exec(io, '/etc/skrc')

        if interactive:
            while not self.halt.is_set():
                #text = await aioconsole.ainput()
                #text = await self.recv(io, '/dev/console')
                text = await io.input()
                if text == '$ exit': break
                #await io.print('cool')
                await self.call(io, f'skrip -e {text}')

    ###
    ### FILE I/O
    ###

    async def get(self, io:Context, path:str):
        """Get file contents."""
        #io = io.fork() if io else Context(self)

        file = self.box(path)
        if not exists(file):
            await io.error(f'!! get path not found: {path}')
            return

        with open(file, 'r', encoding='utf-8') as file:
            return file.read()

    async def exec(self, io:Context, path:str, args:str=None):
        """When you know what you need and you've come prepared (arguments)."""
        #io = io.fork() if io else Context(self)

        file = self.box(path)
        if not exists(file):
            await io.error(f'!! exec path not found: {path}')
            return

        with open(file, 'r') as file:
            shebang = file.readline().rstrip()

        if shebang and shebang.startswith('#!'):
            shebang = shebang[2:]

            if shebang.startswith('/bin/'): # HACK
                args = ' ' + ' '.join(args) if args else ''
                # ugly:
                return await self.call(io, shebang[5:] + ' ' + path + args)

            else:
                await io.error(f'!! bad shebang: {path}')
                return

        else:
            await io.error(f'!! no shebang: {path}')
            # TODO support real binaries (executables), etc.
            return

    async def send(self, io:Context, dev:str, data):
        """Send data to device."""
        #io = io.fork() if io else Context(self)

        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return

        dev = dev[5:]
        #return await getattr(self.dev, dev)(data)
        path = self.box(join('/dev', dev))
        py = self.pymod(f'iosk.dev.{dev}', path)

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

    async def recv(self, io:Context, dev:str):
        """Receive data from device."""
        #io = io.fork() if io else Context(self)

        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return

        dev = dev[5:]
        path = self.box(join('/dev', dev))
        py = self.pymod(f'iosk.dev.{dev}', path)

        if py:
            #print('  SEND PYTHON')
            try:
                return await py.iorecv(io)
            except Exception as e: # FIXME error logging
                await io.error(f'!! error receiving from: /dev/{dev}')
                #return
                raise e

        else:
            print(f'  RECV FILE: {path}')
            #return await self.exec(join('/dev', dev), args)

    ###
    ### FILE OPS
    ###

    async def copy(self, io:Context, from_path:str, to_path:str):
        """Copy file."""
        from_file = self.box(from_path)
        if not exists(from_file):
            await io.error(f'!! copy from path not found: {from_path}')
            return

        to_file = self.box(to_path)
        shutil.copy(from_file, to_file)

    async def move(self, io:Context, from_path:str, to_path:str):
        """Move file/directory."""
        from_file = self.box(from_path)
        if not exists(from_file):
            await io.error(f'!! move from path not found: {from_path}')
            return

        to_file = self.box(to_path)
        shutil.move(from_file, to_file)

    async def remove(self, io:Context, path:str):
        """Remove file."""
        file = self.box(path)
        if not exists(file):
            await io.error(f'!! remove path not found: {path}')
            return

        os.remove(file)

    ###
    ### COMMAND
    ###

    async def call(self, io:Context, args):
        """Interpret arguments for something to invoke (exec)."""
        #io = io.fork() if io else Context(self)

        #print(f'CALL:"{args}"')
        space = args.index(' ') if ' ' in args else len(args)
        cmd = args[:space]
        args = args[space+1:]

        path = self.box(join('/bin', cmd)) # HACK
        modname = f'iosk.bin.{cmd}'
        py = self.pymod(modname, path)

        if py:
            #print('  CALL PYTHON')
            try:
                return await py.iocall(io, args)
            except Exception as e: # FIXME error logging
                await io.error(f'!! error calling: {cmd} {args}')
                #return
                raise e

        else:
            #print('  CALL FILE')
            return await self.exec(io, join('/bin', cmd), args) # HACK

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

