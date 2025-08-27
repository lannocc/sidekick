# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture
from ..util import print_flush as print

import asyncio
import aioconsole
from datetime import datetime
import os
from os.path import join, isdir, exists
import importlib, importlib.util
import sys
import shutil
import traceback


class IOSK:
    BOOT = 0 # current boot number

    CONSOLE_DEV = '/dev/console'
    BOOT_COUNT = '/var/cache/boot'
    INIT_SCRIPT = '/sbin/init'
    SYSTEM_LOG = '/var/log/system'
    USER_LOG = '/var/log/user'
    SKRC = '/etc/skrc'

    def __init__(self, root):
        self.root = root # path
        self.started = None

        self.ready = asyncio.Event()
        self.halt = asyncio.Event()

        self.system = None # Context
        self.users = { } # handle:Context
        self.chat = None

    ###
    ### SYSTEM LIFECYCLE
    ###

    async def start(self):
        print(f'IOSK is starting...')
        self.started = datetime.now()
        fail = None

        if not isdir(self.root):
            fail = 'bad root'

        io = None

        if not fail:
            boot = self.box(self.BOOT_COUNT)
            if exists(boot):
                with open(boot, 'r') as bf:
                    self.BOOT = int(bf.read()) + 1

            chatter = self.box(join(Context.CHATTER, str(self.BOOT)))
            if not exists(chatter):
                os.makedirs(chatter) # creates /var/cache
            elif not isdir(chatter):
                fail = f'not a dir: {chatter}'

            with open(boot, 'w') as boot: # assumes /var/cache exists
                boot.write(str(self.BOOT))

        if not fail:
            io = self.system = Context(self, self.CONSOLE_DEV,
                                       Capture.log(self, self.SYSTEM_LOG, True))

            await io.print(f'IOSK boot number {self.BOOT}...')

        if fail:
            if io: await io.error(f'!! {fail}')
            else: print(f'!! {fail}')
            self.started = None
            self.ready.set()
            return

        ##- init -##
        ok = await self.exec(io, self.INIT_SCRIPT)
        if not ok: return

        await io.print(f'IOSK has started.')

    async def run(self):
        assert self.system
        io = self.system

        await io.print(f'IOSK is ready.')
        self.ready.set()

        await self.halt.wait() # wait here for shutdown
        await io.print(f'IOSK shutdown signal received...')

        for user, uio in self.users.copy().items():
            disconnect = f':: {user} has been disconnected (shutdown)'
            await self.logout(uio, disconnect=disconnect)

        await io.print(f'IOSK system halted.')
        self.system = None

    ###
    ### USER LIFECYCLE
    ###

    async def login(self, user, device, interactive:bool=True,
                    connect=None, io_callback=None):
        """Log-in to get a Context."""
        await self.ready.wait()
        if self.halt.is_set(): return

        if device != self.CONSOLE_DEV \
                and not await self.exists(self.system, device):
            await self.system.error(f'!! device not found: {device}')
            return

        if user in self.users:
            await self.system.error(f'!! already logged in: {user}')
            return

        await self.system.print(f'IOSK login: {user}')

        io = self.system.fork()
        io.log = Capture.log(self, join(self.USER_LOG, user), True)
        io.dev = device
        io.user = user
        io.user_base = True
        self.users[user] = io

        if io_callback:
            await io_callback(io)

        if connect:
            if self.chat: await self.chat.send(user, connect, sys=True)
            else: await io.print(connect)

        skrc = self.box(self.SKRC)
        if exists(skrc):
            await self.exec(io, self.SKRC)

        if interactive:
            self.interactive(io)

        return io

    async def interactive(self, io):
        while not self.halt.is_set():
            start = datetime.now()
            try:
                #text = await io.input('[me] >> ')
                text = await io.input(f'[{io.user}] >> ')

                while text is None: # for non-blocking inputs
                    #print('POLL INPUT')
                    delay = (datetime.now() - start).total_seconds()
                    if delay < 0.1:
                        await asyncio.sleep(0.1 - delay)
                    start = datetime.now()
                    text = await io.input()

                for line in text.split('\n'):
                    line = line.rstrip()
                    if line == '$ exit': return

                    if line.startswith('#') or line.startswith('$ '):
                        await self.call(io, f'skrip -e {line}')

                    elif line:
                        if self.chat: await self.chat.send(io.user, line)
                        else: await io.print(line)

            except EOFError:
                return

    async def logout(self, io:Context, disconnect=None):
        if io.user not in self.users:
            await self.system.error(f'!! not logged in: {io.user}')
            return

        await self.system.print(f'IOSK logout: {io.user}')
        if disconnect:
            if self.chat: await self.chat.send(io.user, disconnect, sys=True)
            else: await io.print(disconnect)
        del self.users[io.user]

    ###
    ### COMMAND
    ###

    async def call(self, io:Context, args):
        """Interpret arguments for something to invoke (exec)."""
        #print(f'CALL:"{args}"')
        space = args.index(' ') if ' ' in args else len(args)
        cmd = args[:space]
        args = args[space+1:]

        path = self.box(join('/bin', cmd)) # HACK
        py = self.pymod(f'bin.{cmd}', path)

        try:
            if py:
                #print(f'CALL PYTHON: {py}')
                #try:
                return await py.iocall(io, args)
                #except Exception as e: # FIXME error logging
                #    await io.error(f'!! error calling: {cmd} {args}')
                    #return
                #    raise e

            else:
                #print('  CALL FILE')
                return await self.exec(io, join('/bin', cmd), args) # HACK

        except Exception as e:
            # FIXME error handling
            await io.error(f'!! exception calling {cmd}')
            traceback.print_exc()

    async def exec(self, io:Context, path:str, args:str=None):
        """When you know what you need and you've come prepared (arguments)."""
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

    ###
    ### FILE OPS
    ###

    async def exists(self, io:Context, path:str):
        """Test if path exists."""
        name = path.replace('/', '.')
        file = self.box(path)
        py = self.pymod(f'proc.exists.{name}', file)
        return py or exists(file)

    async def create(self, io:Context, path:str):
        """Create new (empty) file."""
        file = self.box(path)
        if exists(file): return

        with open(file, 'w') as f:
            pass

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

    async def create_dir(self, io:Context, path:str, parents=False):
        """Create new directory."""
        folder = self.box(path)
        if exists(folder): return

        if parents:
            os.makedirs(folder)

        else:
            os.mkdir(folder)

    async def remove_dir(self, io:Context, path:str):
        """Remove directory."""
        folder = self.box(path)
        if not exists(folder):
            await io.error(f'!! remove dir path not found: {path}')
            return

        os.rmdir(folder)

    ###
    ### FILE I/O
    ###

    async def get(self, io:Context, path:str):
        """Get file contents."""
        file = self.box(path)
        if not exists(file):
            await io.error(f'!! get path not found: {path}')
            return

        with open(file, 'r', encoding='utf-8') as file:
            return file.read()

    async def send(self, io:Context, dev:str, data):
        """Send data to device."""
        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return

        dev = dev[5:]
        #return await getattr(self.dev, dev)(data)
        path = self.box(join('/dev', dev))
        py = self.pymod(f'dev.{dev}', path)

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
        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return

        dev = dev[5:]
        path = self.box(join('/dev', dev))
        py = self.pymod(f'dev.{dev}', path)

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
        modname = f'sk.iosk.{modname}'
        if not path.endswith('.py'): path += '.py'
        #print(f'IMPORT {modname} at {path}')

        if modname in sys.modules:
            # TODO: check for file modification / reload?
            #print(f'MOD FOUND: {modname}: {sys.modules[modname]}')
            return sys.modules[modname]

        py = None
        try:
            spec = importlib.util.spec_from_file_location(modname, path)
            #print(f'SPEC: {spec}')
            mod = importlib.util.module_from_spec(spec)
            #print(f'SETTING SYS MOD {modname}: {mod}')
            spec.loader.exec_module(mod)
            sys.modules[modname] = mod
            py = mod
            #print(f'PY1: {py}')
        except:
            py = None

        if not py:
            # original way
            py = None
            try: py = importlib.import_module(modname)
            except ModuleNotFoundError: pass
            #print(f'PY2: {py}')

        return py

