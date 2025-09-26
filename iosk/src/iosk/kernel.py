# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture, print_flush as print

from binaryornot.check import is_binary

import shlex
import re
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

        # --- CWD and Home Directory Initialization ---
        home_dir_virtual = f'/home/{user}'
        # Box the home directory path to get its actual location on the host filesystem.
        # Pass io_context=io for consistency, though an absolute path ignores io.pwd in box().
        home_dir_host = self.box(home_dir_virtual, io_context=io)

        if not os.path.exists(home_dir_host):
            try:
                os.makedirs(home_dir_host)
                await io.print(f":: created home directory: {home_dir_virtual}")
            except Exception as e:
                await self.system.error(f"!! failed to create home directory {home_dir_virtual}: {e}")
                # For now, allow login to proceed but log the error.

        io.pwd = home_dir_virtual # Set the current working directory for the user

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

    async def call(self, io:Context, args:str):
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
            return False

        if not argv_raw:
            return True

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
        cmd_args = argv[1:]

        resolved_internal_path = None # This will store the internal sandboxed path, e.g., '/bin/ls'
        is_python_module = False

        potential_base_paths = [] # Paths relative to the sandboxed root, e.g., '/bin/ls' or 'mycmd'

        # Case 1: Command is an absolute or explicit relative path (e.g., /usr/local/bin/mytool, ./script.sh)
        if cmd.startswith('/') or cmd.startswith('./') or cmd.startswith('../'):
            potential_base_paths.append(cmd)
        else:
            # Case 2: Command is a bare name, search PATH or default to /bin
            path_env = io.environ().get('PATH')
            if path_env:
                path_dirs = path_env.split(os.pathsep)
                for p_dir in path_dirs:
                    if p_dir: # Ensure path_dir is not empty
                        potential_base_paths.append(join(p_dir, cmd))
            else:
                # Default to /bin if PATH is not set
                potential_base_paths.append(join('/bin', cmd))

        # Search through potential_base_paths to find the executable
        for p_base in potential_base_paths:
            # 2a. Try to find it as a Python module (.py file)
            sandboxed_py_path = self.box(f'{p_base}.py', io_context=io)
            if exists(sandboxed_py_path):
                # We need to confirm it's a valid Python module before setting resolved_internal_path
                # without actually importing it yet.
                modname_for_spec = f'sk.iosk.{p_base.strip("/").replace("/", ".")}'
                try:
                    spec = importlib.util.spec_from_file_location(modname_for_spec, sandboxed_py_path)
                    if spec and spec.loader:
                        resolved_internal_path = p_base
                        is_python_module = True
                        break # Found a Python module, prioritize it
                except Exception:
                    # Ignore errors in spec creation, means it's not a valid Python module for us
                    pass

            # 2b. If not a Python module, try to find it as a regular executable (e.g., a skrip script)
            if not resolved_internal_path: # Only check if not already resolved as Python module
                sandboxed_file_path = self.box(p_base, io_context=io)
                if exists(sandboxed_file_path) and isfile(sandboxed_file_path):
                    resolved_internal_path = p_base
                    is_python_module = False # Explicitly not a Python module for iocall
                    break # Found a script/executable

        if not resolved_internal_path:
            await io.error(f"!! command not found: {cmd}")
            return False

        # --- Execution ---
        try:
            if is_python_module:
                # Load the Python module for real and call its iocall
                modname_for_pymod = resolved_internal_path.strip("/").replace("/", ".")
                # pymod will prepend 'sk.iosk.' to this name during import
                py_mod = self.pymod(modname_for_pymod, self.box(f'{resolved_internal_path}.py'))
                if py_mod and hasattr(py_mod, 'iocall'):
                    return await py_mod.iocall(io, cmd_args)
                else:
                    await io.error(f"!! Python module {resolved_internal_path}.py found but missing iocall method.")
                    return False
            else:
                # Execute as a script (e.g., skrip) using self.exec
                # self.exec will handle shebang logic and then potentially call self.call again
                return await self.exec(io, resolved_internal_path, cmd_args)
        except Exception as e:
            await io.error(f'!! exception calling {cmd}: {e}')
            traceback.print_exc()
            return False


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
        """Test if path exists."""
        name = path.replace('/', '.') # Used only for pymod name, not path resolution
        file = self.box(path, io_context=io)
        py = self.pymod(f'proc.exists.{name}', file)
        return py or exists(file)

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

        to_file = self.box(to_path, io_context=io)
        shutil.copy(from_file, to_file)
        return True

    async def move(self, io:Context, from_path:str, to_path:str):
        """Move file/directory."""
        from_file = self.box(from_path, io_context=io)
        if not exists(from_file):
            await io.error(f'!! move from path not found: {from_path}')
            return False

        to_file = self.box(to_path, io_context=io)
        shutil.move(from_file, to_file) # shutil.move handles both file and dir
        return True

    async def remove(self, io:Context, path:str):
        """Remove file."""
        file = self.box(path, io_context=io)
        if not exists(file):
            await io.error(f'!! remove path not found: {path}')
            return False

        os.remove(file)
        return True

    async def create_dir(self, io:Context, path:str, parents=False):
        """Create new directory."""
        folder = self.box(path, io_context=io)
        if exists(folder):
            await io.error(f'!! path already exists: {path}')
            return False

        if parents: os.makedirs(folder)
        else: os.mkdir(folder)
        return True

    async def remove_dir(self, io:Context, path:str):
        """Remove directory."""
        folder = self.box(path, io_context=io)
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

