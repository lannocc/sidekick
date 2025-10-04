# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture, print_flush as print
from .parser import CommandLineParser
from .pipeline import CommandPipelineExecutor

from binaryornot.check import is_binary
import tiktoken

import shlex
import asyncio
import aioconsole
from datetime import datetime
import os
from os.path import join, isdir, isfile, exists
import importlib, importlib.util
import sys
import shutil
import traceback
from io import StringIO


class IOSK:
    BOOT = 0 # current boot number

    CONSOLE_DEV = '/dev/console'
    BOOT_COUNT = '/var/cache/boot'
    INIT_SCRIPT = '/sbin/init'
    SYSTEM_LOG = '/var/log/system'
    USER_LOG = '/var/log/user'
    SKRC = '/etc/skrc'
    SKEL_SKRC = '/etc/skel/skrc' # Added for the new requirement

    def __init__(self, root):
        self.root = root # path
        self.started = None

        self.ready = asyncio.Event()
        self.halt = asyncio.Event()

        self.system = None # Context
        self.users = { } # handle:Context
        self.chat = None

        self.parser = CommandLineParser(self)
        self.pipeline_executor = CommandPipelineExecutor(self) # Instantiate the executor

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
        io.banks = { } # A user's base context gets its own banks.
        io.log = Capture.log(self, join(self.USER_LOG, user), True)
        io.dev = device
        io.user = user
        io.su = device in (self.CONSOLE_DEV, '/dev/terminal') # if you have console, you're super
        io.base = True
        io.bot = device not in (self.CONSOLE_DEV, '/dev/terminal')
        self.users[user] = io

        # --- CWD and Home Directory Initialization ---
        home_dir_virtual = f'/home/{user}'
        # Box the home directory path to get its actual location on the host filesystem.
        # Pass io_context=io for consistency, though an absolute path ignores io.pwd in box().
        home_dir_host = self.box(home_dir_virtual, io_context=io)

        if not os.path.exists(home_dir_host):
            try:
                os.makedirs(home_dir_host)
                await io.print(f":: created home directory: {home_dir_virtual}")

                # Copy /etc/skel/skrc to ~/.skrc if it exists
                skel_skrc_path = self.SKEL_SKRC
                user_skrc_path = join(home_dir_virtual, '.skrc')
                if await self.exists(io, skel_skrc_path):
                    await io.print(f":: copying {skel_skrc_path} to {user_skrc_path}")
                    await self.copy(io, skel_skrc_path, user_skrc_path)

            except Exception as e:
                await self.system.error(f"!! failed to create home directory {home_dir_virtual}: {e}")
                # For now, allow login to proceed but log the error.

        io.pwd = home_dir_virtual # Set the current working directory for the user

        if io_callback:
            await io_callback(io)

        if connect:
            if self.chat: await self.chat.send(user, connect, sys=True)
            else: await io.print(connect)

        # Execute system-wide skrc
        skrc_global_path = self.SKRC
        if exists(self.box(skrc_global_path)):
            await self.exec(io, skrc_global_path)

        # Execute user-specific .skrc
        skrc_user_path = join('/home', user, '.skrc')
        if exists(self.box(skrc_user_path)):
            await self.exec(io, skrc_user_path)

        if interactive:
            await self.interactive(io)

        return io

    async def interactive(self, io):
        while not self.halt.is_set():
            start = datetime.now()
            try:
                while (text := await io.input(f'[{io.user} {io.pwd}] >> ')) is None:
                    # non-blocking inputs return None until data
                    delay = (datetime.now() - start).total_seconds()
                    if delay < 0.1:
                        await asyncio.sleep(0.1 - delay)
                    start = datetime.now()

                for line in text.split('\n'):
                    line = line.rstrip()
                    if line == '$ exit': return

                    if line.startswith('#'):
                        pass

                    elif line.startswith('$ '):
                        command_line = line[2:]
                        if command_line: # Don't add empty commands to history
                            io.history.append(command_line)
                        await self.call(io, command_line) # Pass the string after '$ '

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

    async def call(self, io:Context, args:str):
        """Interpret arguments, parse for pipes/redirection, and invoke commands."""
        # Delegate the entire pipeline execution to the CommandPipelineExecutor
        return await self.pipeline_executor.execute_pipeline(io, args, self.parser)

    async def exec(self, io:Context, path:str, argv:list=None):
        """When you know what you need and you've come prepared (arguments).
        This method expects `path` to be an absolute path within the sandboxed
        filesystem (e.g., /bin/myscript). It does not search the PATH environment
        variable for the executable itself."""
        if argv is None:
            argv = []

        file = self.box(path) # path is expected to be an absolute virtual path from `call`
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
        """Test if path exists, considering both physical files and Python modules."""
        # 1. Check for physical file/directory existence on the sandboxed filesystem.
        file_on_host = self.box(path, io_context=io)
        if exists(file_on_host):
            return True

        # 2. Check if a corresponding Python module file exists in the sandbox.
        # This handles cases like `exists('/bin/ls')` being true if `root/bin/ls.py` exists.
        py_file_on_host = self.box(f'{path}.py', io_context=io)
        if exists(py_file_on_host) and isfile(py_file_on_host):
            return True

        # 3. Check for a "built-in" Python module that is part of the iosk source
        # but not present as a file in the sandboxed filesystem (e.g., /dev/google).

        # First, resolve the path to an absolute virtual path to be safe.
        if io and io.pwd and not path.startswith('/'):
            virtual_path = os.path.normpath(os.path.join(io.pwd, path))
        else:
            virtual_path = os.path.normpath(path)

        # Convert virtual path to module path suffix, e.g., '/dev/google' -> 'dev.google'
        mod_suffix = virtual_path.lstrip('/')
        if not mod_suffix:
            return False # Path was just '/'

        # The convention is to find modules relative to the 'iosk' package.
        # Example: /dev/google -> dev.google -> iosk.dev.google
        full_mod_name = f'iosk.{mod_suffix.replace("/", ".")}'

        try:
            # Use find_spec to check for module existence without importing it.
            spec = importlib.util.find_spec(full_mod_name)
            if spec is not None:
                return True
        except (ModuleNotFoundError, ValueError):
            # An invalid module path could raise an error.
            pass

        return False

    async def create(self, io:Context, path:str):
        """Create new (empty) file."""
        file = self.box(path, io_context=io)
        if exists(file): return True # Already exists, idempotent

        with open(file, 'w') as f:
            pass
        return True

    async def copy(self, io:Context, from_path:str, to_path:str):
        """Copy file."""
        from_file = self.box(from_path, io_context=io)
        if not exists(from_file):
            await io.error(f'!! copy from path not found: {from_path}')
            return False

        # Ensure the destination directory exists for the target file
        to_file_host = self.box(to_path, io_context=io)
        to_dir_host = os.path.dirname(to_file_host)
        if not exists(to_dir_host):
            try:
                os.makedirs(to_dir_host)
            except OSError as e:
                await io.error(f"!! failed to create destination directory for copy '{to_path}': {e}")
                return False

        shutil.copy(from_file, to_file_host)
        return True

    async def move(self, io:Context, from_path:str, to_path:str):
        """Move file/directory."""
        from_file = self.box(from_path, io_context=io)
        if not exists(from_file):
            await io.error(f'!! move from path not found: {from_path}')
            return False

        # Ensure the destination directory exists for the target file
        to_file_host = self.box(to_path, io_context=io)
        to_dir_host = os.path.dirname(to_file_host)
        if not exists(to_dir_host):
            try:
                os.makedirs(to_dir_host)
            except OSError as e:
                await io.error(f"!! failed to create destination directory for move '{to_path}': {e}")
                return False

        shutil.move(from_file, to_file_host) # shutil.move handles both file and dir
        return True

    async def remove(self, io:Context, path:str):
        """Remove file."""
        file = self.box(path, io_context=io)
        if not exists(file):
            await io.error(f'!! remove path not found: {path}')
            return False

        if isdir(file): # Prevent removing a directory with os.remove
            await io.error(f'!! path is a directory, use rmdir: {path}')
            return False

        os.remove(file)
        return True

    async def create_dir(self, io:Context, path:str, parents=False):
        """Create new directory."""
        folder = self.box(path, io_context=io)
        if exists(folder):
            await io.error(f'!! path already exists: {path}')
            return False # Changed to False as it already exists, not an error but not 'created new'

        try:
            if parents: os.makedirs(folder)
            else: os.mkdir(folder)
            return True
        except OSError as e:
            await io.error(f"!! failed to create directory '{path}': {e}")
            return False

    async def remove_dir(self, io:Context, path:str):
        """Remove directory."""
        folder = self.box(path, io_context=io)
        if not exists(folder):
            await io.error(f'!! remove dir path not found: {path}')
            return False
        if not isdir(folder):
            await io.error(f'!! path is not a directory: {path}')
            return False

        try:
            os.rmdir(folder)
            return True
        except OSError as e:
            await io.error(f"!! failed to remove directory '{path}': {e}")
            return False

    ###
    ### FILE I/O
    ###

    async def get(self, io:Context, path:str):
        """Get file contents."""
        file = self.box(path, io_context=io)
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

    async def recv(self, io:Context, dev:str, prompt=None):
        """Receive data from device."""
        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return None

        dev = dev[5:]
        path = self.box(join('/dev', dev))
        py = self.pymod(f'dev.{dev}', path)

        if py:
            try:
                return await py.iorecv(io, prompt=prompt)
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

    def box(self, virtual_path_input: str, io_context=None) -> str:
        """
        Sandboxes a given virtual path to the host filesystem.
        If io_context is provided and the path is relative, it resolves it relative to io_context.pwd.
        Returns the absolute host filesystem path.
        """
        # Step 1: Determine the effective virtual path
        effective_virtual_path = virtual_path_input
        if io_context and io_context.pwd and not virtual_path_input.startswith('/'):
            # Path is relative, resolve it against the current working directory of the context
            effective_virtual_path = os.path.join(io_context.pwd, virtual_path_input)

        # Step 2: Normalize the virtual path to handle '.', '..', and multiple slashes
        # This converts paths like '/a/./b' to '/a/b' and '/a/../b' to '/b'
        normalized_virtual_path = os.path.normpath(effective_virtual_path)

        # Step 3: Ensure the normalized path is absolute within the virtual filesystem
        # os.path.normpath might return '..' if the path resolves above the virtual root (e.g., /a/../../b -> /b)
        if not normalized_virtual_path.startswith('/'):
            normalized_virtual_path = '/' + normalized_virtual_path

        # Step 4: Convert the normalized virtual path into a host path by joining it with self.root
        # Strip the leading '/' from the normalized virtual path for os.path.join
        path_relative_to_virtual_root = normalized_virtual_path.lstrip('/')
        host_path = os.path.join(self.root, path_relative_to_virtual_root)
        abs_path = os.path.abspath(host_path)

        return abs_path

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

