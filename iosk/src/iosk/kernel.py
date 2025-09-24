# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture, print_flush as print

from binaryornot.check import is_binary

import shlex # Added for shell parsing
import re # Added for variable expansion
import asyncio
import aioconsole
from datetime import datetime
import os
from os.path import join, isdir, isfile, exists
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

        if not fail:
            code = self.box(Context.CODE)
            if not exists(code):
                os.makedirs(code)
            elif not isdir(code):
                fail = f'not a dir: {code}'

        if not fail:
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
        #-------------------------------------------------#
        await io.print(f'IOSK shutdown signal received...')

        for user, uio in self.users.copy().items():
            disconnect = f':: {user} has been disconnected (shutdown)'
            await self.logout(uio, disconnect=disconnect)

        await io.print(f'IOSK system halted.')
        self.system = None

    ###
    ### USER LIFECYCLE
    ###

    async def login(self, user, device=None, interactive:bool=True,
                    connect=None, io_callback=None):
        """Log-in to get a Context."""
        await self.ready.wait()
        if self.halt.is_set(): return

        if not device:
            device = self.CONSOLE_DEV

        elif device != self.CONSOLE_DEV \
                and not await self.exists(self.system, device):
            await self.system.error(f'!! device not found: {device}')
            return

        if user in self.users:
            await self.system.error(f'!! already logged in: {user}')
            return

        elif user == 'iosk': # reserved
            await self.system.error(f'!! invalid login name: {user}')
            return

        await self.system.print(f'IOSK login: {user}')

        io = self.system.fork()
        io.log = Capture.log(self, join(self.USER_LOG, user), True)
        io.dev = device
        io.user = user
        io.su = device == self.CONSOLE_DEV # if you have console, you're super
        io.base = True
        io.bot = device != self.CONSOLE_DEV
        self.users[user] = io

        if io_callback:
            await io_callback(io)

        if connect:
            if self.chat: await self.chat.send(user, connect, sys=True)
            else: await io.print(connect)

        skrc = self.box(self.SKRC)
        if exists(skrc):
            await self.exec(io, self.SKRC)

        skrc = join('/home', user, '.skrc')
        if exists(self.box(skrc)):
            #print('@@@@@@@@@@@@@ HERE WE GO @@@@@@@@@@@@@')
            await self.exec(io, skrc)

        if interactive:
            await self.interactive(io)

        return io

    async def interactive(self, io):
        while not self.halt.is_set():
            start = datetime.now()
            try:
                while (text := await io.input(f'[{io.user}] >> ')) is None:
                    # non-blocking inputs return None until data
                    #print('POLL INPUT')
                    delay = (datetime.now() - start).total_seconds()
                    if delay < 0.1:
                        await asyncio.sleep(0.1 - delay)
                    start = datetime.now()

                for line in text.split('\n'):
                    line = line.rstrip()
                    if line == '$ exit': return

                    if line.startswith('#'):
                        #await io.comment(line)
                        pass

                    elif line.startswith('$ '):
                        # The interactive shell passes the command line string directly
                        # to self.call, just like a skrip file or other internal calls.
                        await self.call(io, line[2:]) # Pass the string after '$ '

                    elif line:
                        if self.chat: await self.chat.send(io.user, line)
                        else: await io.print(line)

            except EOFError:
                return

    async def logout(self, io:Context, disconnect=None):
        if io.user not in self.users:
            await self.system.error(f'!! not logged in: {io.user}')
            return False

        await self.system.print(f'IOSK logout: {io.user}')
        if disconnect:
            if self.chat: await self.chat.send(io.user, disconnect, sys=True)
            else: await io.print(disconnect)
        del self.users[io.user]
        return True

    ###
    ### COMMAND
    ###

    async def call(self, io:Context, args:str): # args is the raw command string
        """Interpret arguments for something to invoke (exec)."""
        # Alias resolution: check if the command is an alias.
        first_space_idx = args.find(' ')
        cmd_candidate = args[:first_space_idx] if first_space_idx != -1 else args
        cmd_rest_of_line = args[first_space_idx+1:] if first_space_idx != -1 else ''

        if cmd_candidate in io.aliases:
            alias_value = io.aliases[cmd_candidate]
            args = f"{alias_value} {cmd_rest_of_line}".strip()

        # 1. Tokenization with shlex
        try:
            argv_raw = shlex.split(args)
        except ValueError as e:
            await io.error(f"!! parse error: {e}")
            return False # Indicate failure

        if not argv_raw:
            return True # Empty command, nothing to do.

        # 2. Variable Expansion
        argv = []
        for token in argv_raw:
            expanded_token = token
            # Support $VAR and ${VAR}
            # Replace $VAR
            expanded_token = re.sub(r'\$(\w+)', lambda m: io.environ().get(m.group(1), ''), expanded_token)
            # Replace ${VAR}
            expanded_token = re.sub(r'\$\{(\w+)\}', lambda m: io.environ().get(m.group(1), ''), expanded_token)
            argv.append(expanded_token)

        cmd = argv[0]
        cmd_args = argv[1:] # Arguments excluding the command name itself
        
        path = self.box(join('/bin', cmd))
        py = self.pymod(f'bin.{cmd}', path)

        try:
            if py:
                return await py.iocall(io, cmd_args) # Pass list of args (list[str])
            else:
                return await self.exec(io, join('/bin', cmd), cmd_args) # Pass list of args (list[str])
        except Exception as e:
            await io.error(f'!! exception calling {cmd}: {e}') # Added error to output
            traceback.print_exc()
            return False # Indicate failure

    async def exec(self, io:Context, path:str, argv:list=None): # Changed args:str to argv:list
        """When you know what you need and you've come prepared (arguments)."""
        if argv is None:
            argv = [] # Default to empty list for consistency

        file = self.box(path)
        if not exists(file):
            await io.error(f'!! exec path not found: {path}')
            return False # Indicate failure

        with open(file, 'r') as file:
            shebang = file.readline().rstrip()

        if shebang and shebang.startswith('#!'):
            shebang = shebang[2:]

            if shebang.startswith('/bin/'): # HACK
                interpreter = shebang[5:] # e.g., 'skrip'

                # The script path itself is an implicit argument to the interpreter
                # followed by the arguments passed to the script.
                script_and_args_for_interpreter = [path] + argv

                # The interpreter's name is the command, and the script to run
                # (plus any of its own arguments) are the arguments for the interpreter.
                interpreter_full_command = [interpreter] + script_and_args_for_interpreter

                # Call the interpreter using the main `self.call` method.
                # self.call will parse this new command string and invoke skrip.py correctly,
                # which will then execute the contents of the target script file.
                return await self.call(io, shlex.join(interpreter_full_command))

            else:
                await io.error(f'!! bad shebang: {path}')
                return False # Indicate failure

        else:
            await io.error(f'!! no shebang: {path}')
            # TODO support real binaries (executables), etc.
            return False # Indicate failure

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
        if exists(file): return True # Already exists, idempotent

        with open(file, 'w') as f:
            pass
        return True

    async def copy(self, io:Context, from_path:str, to_path:str):
        """Copy file."""
        from_file = self.box(from_path)
        if not exists(from_file):
            await io.error(f'!! copy from path not found: {from_path}')
            return False

        to_file = self.box(to_path)
        shutil.copy(from_file, to_file)
        return True

    async def move(self, io:Context, from_path:str, to_path:str):
        """Move file/directory."""
        from_file = self.box(from_path)
        if not exists(from_file):
            await io.error(f'!! move from path not found: {from_path}')
            return False

        to_file = self.box(to_path)
        shutil.move(from_file, to_file)
        return True

    async def remove(self, io:Context, path:str):
        """Remove file."""
        file = self.box(path)
        if not exists(file):
            await io.error(f'!! remove path not found: {path}')
            return False

        os.remove(file)
        return True

    async def create_dir(self, io:Context, path:str, parents=False):
        """Create new directory."""
        folder = self.box(path)
        if exists(folder):
            await io.error(f'!! path already exists: {path}')
            return False

        if parents: os.makedirs(folder)
        else: os.mkdir(folder)
        return False # Should return True on success

    async def remove_dir(self, io:Context, path:str):
        """Remove directory."""
        folder = self.box(path)
        if not exists(folder):
            await io.error(f'!! remove dir path not found: {path}')
            return False

        os.rmdir(folder)
        return True

    ###
    ### FILE I/O
    ###

    async def get(self, io:Context, path:str):
        """Get file contents."""
        file = self.box(path)
        if not exists(file):
            await io.error(f'!! path not found: {path}')
            return None # Return None on error

        if not isfile(file):
            await io.error(f'!! not a file: {path}')
            return None # Return None on error

        if is_binary(file):
            await io.error(f'!! refusing binary file: {path}')
            return None # Return None on error

        with open(file, 'r', encoding='utf-8') as file:
            return file.read()

    async def send(self, io:Context, dev:str, data):
        """Send data to device."""
        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return False

        dev = dev[5:]
        path = self.box(join('/dev', dev))
        py = self.pymod(f'dev.{dev}', path)

        if py:
            try:
                return await py.iosend(io, data)
            except Exception as e:
                await self.system.error(f'!! error sending to /dev/{dev}: {e}')
                traceback.print_exc()
                return False
        else:
            await io.error(f'!! no handler for device: {dev}')
            return False

    async def recv(self, io:Context, dev:str):
        """Receive data from device."""
        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return None

        dev = dev[5:]
        path = self.box(join('/dev', dev))
        py = self.pymod(f'dev.{dev}', path)

        if py:
            try:
                return await py.iorecv(io)
            except Exception as e:
                await self.system.error(f'!! error receiving from /dev/{dev}: {e}')
                traceback.print_exc()
                return None
        else:
            await io.error(f'!! no handler for device: {dev}')
            return None

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

        py = None
        try:
            spec = importlib.util.spec_from_file_location(modname, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.modules[modname] = mod
            py = mod
        except:
            py = None

        if not py:
            py = None
            try: py = importlib.import_module(modname)
            except ModuleNotFoundError: pass

        return py

