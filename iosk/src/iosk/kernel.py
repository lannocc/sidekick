# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture, print_flush as print
from .parser import CommandLineParser

from binaryornot.check import is_binary

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

    def __init__(self, root):
        self.root = root # path
        self.started = None

        self.ready = asyncio.Event()
        self.halt = asyncio.Event()

        self.system = None # Context
        self.users = { } # handle:Context
        self.chat = None

        self.parser = CommandLineParser(self)

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
        # Step 1: Alias resolution
        first_space_idx = args.find(' ')
        cmd_candidate = args[:first_space_idx] if first_space_idx != -1 else args
        cmd_rest_of_line = args[first_space_idx+1:] if first_space_idx != -1 else ''

        alias_resolved_args = args
        if cmd_candidate in io.aliases:
            alias_value = io.aliases[cmd_candidate]
            alias_resolved_args = f"{alias_value} {cmd_rest_of_line}".strip()

        # Step 2: Parsing, Substitution, Expansion, Tokenization
        argv = await self.parser.parse_and_tokenize(io, alias_resolved_args)

        if argv is None: # Parsing failed
            return False
        if not argv: # Empty command line
            return True

        # Step 3: Pipeline and Redirection Parsing
        commands = []
        current_command = []
        redirect_out_path = None
        redirect_append = False

        i = 0
        while i < len(argv):
            token = argv[i]
            if token == '|':
                if not current_command:
                    await io.error("!! parse error: empty command before pipe")
                    return False
                commands.append(current_command)
                current_command = []
            elif token in ('>', '>>'):
                if i + 1 >= len(argv):
                    await io.error(f"!! parse error: missing filename for redirection '{token}'")
                    return False
                if redirect_out_path:
                    await io.error("!! parse error: multiple redirections are not supported")
                    return False
                redirect_out_path = argv[i+1]
                redirect_append = (token == '>>')
                i += 1 # Skip the filename token
            else:
                current_command.append(token)
            i += 1

        if current_command:
            commands.append(current_command)
        elif commands: # Case like `ls |`
            await io.error("!! parse error: empty command after pipe")
            return False

        if not commands:
            return True

        # Step 4: Differentiate between simple command and pipeline
        num_commands = len(commands)

        # If it's a single command with no redirection, execute it directly in the current context.
        if num_commands == 1 and not redirect_out_path:
            return await self._execute_single_command(io, commands[0])

        # Otherwise, handle the full pipeline with forked contexts.
        # Step 4b: Pipeline Execution
        pipe_buffer = None
        success = True

        for idx, command_argv in enumerate(commands):
            is_last_cmd = (idx == num_commands - 1)

            cmd_io = io.fork()

            # Configure stdin from the previous command's output
            if pipe_buffer:
                pipe_buffer.seek(0)
                cmd_io.stdin = pipe_buffer

            redirect_file_handle = None
            try:
                # Configure stdout
                if is_last_cmd and redirect_out_path:
                    mode = 'a' if redirect_append else 'w'
                    host_path = self.box(redirect_out_path, io_context=io)
                    parent_dir = os.path.dirname(host_path)
                    if not os.path.exists(parent_dir): os.makedirs(parent_dir)
                    redirect_file_handle = open(host_path, mode, encoding='utf-8')
                    cmd_io.stdout = redirect_file_handle
                elif not is_last_cmd:
                    pipe_buffer = StringIO()
                    cmd_io.stdout = pipe_buffer
                else:
                    # For the last command in a pipe without redirection, it should inherit
                    # the original io's stdout (which could be the console or another redirect).
                    cmd_io.stdout = io.stdout

                # Execute the single command segment
                success = await self._execute_single_command(cmd_io, command_argv)

            except Exception as e:
                await io.error(f"!! error during pipeline execution: {e}")
                traceback.print_exc()
                success = False
            finally:
                if redirect_file_handle:
                    redirect_file_handle.close()

            if not success:
                break # If any command fails, stop the pipeline

        return success

    async def _execute_single_command(self, io: Context, argv: list) -> bool:
        """Resolves and executes a single command with its arguments."""
        if not argv:
            return True

        cmd = argv[0]
        cmd_args = argv[1:]

        resolved_internal_path = None
        is_python_module = False
        potential_base_paths = []

        if cmd.startswith('/') or cmd.startswith('./') or cmd.startswith('../'):
            if cmd.startswith('./') or cmd.startswith('../'):
                potential_base_paths.append(os.path.normpath(os.path.join(io.pwd if io.pwd else '/', cmd)))
            else:
                potential_base_paths.append(cmd)
        else:
            path_env = io.environ().get('PATH', '/bin')
            path_dirs = path_env.split(os.pathsep)
            for p_dir in path_dirs:
                if p_dir:
                    potential_base_paths.append(join(p_dir, cmd))

        for p_base in potential_base_paths:
            sandboxed_py_path = self.box(f'{p_base}.py', io_context=io)
            if exists(sandboxed_py_path) and isfile(sandboxed_py_path):
                modname_for_spec = f'sk.iosk.{p_base.strip("/").replace("/", ".")}'
                try:
                    spec = importlib.util.spec_from_file_location(modname_for_spec, sandboxed_py_path)
                    if spec and spec.loader:
                        resolved_internal_path = p_base
                        is_python_module = True
                        break
                except Exception:
                    pass

            sandboxed_file_path = self.box(p_base, io_context=io)
            if exists(sandboxed_file_path) and isfile(sandboxed_file_path):
                resolved_internal_path = p_base
                is_python_module = False
                break

        if not resolved_internal_path:
            await io.error(f"!! command not found: {cmd}")
            return False

        try:
            if is_python_module:
                modname_for_pymod = resolved_internal_path.strip("/").replace("/", ".")
                py_mod = self.pymod(modname_for_pymod, self.box(f'{resolved_internal_path}.py'))
                if py_mod and hasattr(py_mod, 'iocall'):
                    result = await py_mod.iocall(io, cmd_args)
                    return result is not False
                else:
                    await io.error(f"!! Python module {resolved_internal_path}.py found but missing iocall method.")
                    return False
            else:
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

