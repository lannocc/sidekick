# src/iosk/kernel.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture, print_flush as print
from .parser import CommandLineParser
from .pipeline import CommandPipelineExecutor
from .chat import AIMessenger
from .port import PortManager

from binaryornot.check import is_binary
import tiktoken

import shlex
import asyncio
import aioconsole
from datetime import datetime, timedelta
import os
from os.path import join, isdir, isfile, exists
import importlib, importlib.util
import sys
import shutil
import traceback
from io import StringIO


# Added for the process management proposal
class Process:
    """A lightweight wrapper to represent a single, ongoing command execution."""
    def __init__(self, pid, user, command, start_time, task):
        self.pid = pid
        self.user = user
        self.command_str = ' '.join(command) # Store the command as a string
        self.start_time = start_time
        self.task = task


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
        
        # Netroom subsystems
        self.port: PortManager = None
        self.chat: AIMessenger = None

        # Netroom state
        self.hostname: str = 'localhost'
        self.network_users: dict = {}
        self.network_rooms: dict = {}

        self.parser = CommandLineParser(self)
        self.pipeline_executor = CommandPipelineExecutor(self) # Instantiate the executor

        # Added for process management proposal
        self.process_table = {}
        self.next_pid = 1

        # Added for per-user clients proposal
        self.device_clients = {}

        # Added for trace proposal
        self.trace_states = {'trip': False}
        self.device_trip_counters = {}

        # Added for token_rate proposal
        self.device_tpm_trackers = {}
        self.device_cooldowns = {}

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

        # Added for trace proposal
        if not fail:
            trip_log_dir = self.box('/var/log/trip')
            if not exists(trip_log_dir):
                os.makedirs(trip_log_dir)
            elif not isdir(trip_log_dir):
                fail = f'not a dir: {trip_log_dir}'

        if not fail:
            with open(boot, 'w') as boot: # assumes /var/cache exists
                boot.write(str(self.BOOT))

        if not fail:
            io = self.system = Context(self, self.CONSOLE_DEV,
                                       Capture.log(self, self.SYSTEM_LOG, True))

            await io.print(f'IOSK boot number {self.BOOT}...')

        if not fail:
            # Read hostname
            hostname_path = self.box('/etc/hostname')
            if exists(hostname_path):
                with open(hostname_path, 'r') as f:
                    self.hostname = f.read().strip() or 'localhost'
            else:
                self.hostname = os.path.basename(os.path.abspath(self.root)) or 'localhost'
            
            # Instantiate subsystems
            self.port = PortManager(self)
            self.chat = AIMessenger(self)
            await io.print(f'System hostname: {self.hostname}')

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

        if self.port:
            await self.port.stop()

        for user, uio in self.users.copy().items():
            disconnect = f':: {user} has been disconnected (shutdown)'
            await self.logout(uio, disconnect=disconnect)

        await io.print(f'IOSK system halted.')
        self.system = None

    ###
    ### TOKEN RATE
    ###

    def _get_current_tpm(self, device_path: str) -> int:
        """
        Calculates the current tokens-per-minute for a device and prunes old entries.
        Returns the sum of tokens used in the last 60 seconds.
        """
        if device_path not in self.device_tpm_trackers:
            return 0

        now = datetime.now()
        one_minute_ago = now - timedelta(seconds=60)
        
        # Filter out old entries and calculate the sum of recent tokens
        recent_entries = [
            (ts, count) for ts, count in self.device_tpm_trackers[device_path]
            if ts > one_minute_ago
        ]
        
        # Update the tracker with the pruned list
        self.device_tpm_trackers[device_path] = recent_entries
        
        # Return the sum of tokens from the recent entries
        return sum(count for _, count in recent_entries)

    async def enforce_cooldown(self, device_path: str, delay_seconds: float):
        """
        Enforces a system-wide cooldown for a specific device.
        """
        if device_path not in self.device_cooldowns:
            # If the event doesn't exist, create it. It defaults to 'set' (ready).
            self.device_cooldowns[device_path] = asyncio.Event()
            self.device_cooldowns[device_path].set()

        event = self.device_cooldowns[device_path]
        
        # Clear the event to signal that the device is now unavailable
        event.clear()
        
        # Wait for the specified delay
        await asyncio.sleep(delay_seconds)
        
        # Set the event to signal that the device is ready again
        event.set()

    async def await_device_readiness(self, user: str, device_path: str, tokens_in_prompt: int):
        """
        Waits for a device to be ready, handling both reactive cooldowns
        and proactive throttling based on TPM.
        """
        # --- Reactive Cooldown Wait ---
        if device_path not in self.device_cooldowns:
            self.device_cooldowns[device_path] = asyncio.Event()
            self.device_cooldowns[device_path].set()

        event = self.device_cooldowns[device_path]
        await event.wait() # This will block if the device is in cooldown

        # --- Proactive Throttling ---
        # Define a threshold, e.g., 95% of 1M TPM
        TPM_QUOTA = 1_000_000
        TPM_THRESHOLD = 950_000

        while True: # Loop to re-check after sleeping
            current_tpm = self._get_current_tpm(device_path)
            
            if current_tpm + tokens_in_prompt <= TPM_THRESHOLD:
                # We are under the threshold, safe to proceed
                break

            # We are over the threshold, need to wait.
            # Find the oldest entry in the tracker to determine how long to sleep.
            tracker = self.device_tpm_trackers.get(device_path, [])
            if not tracker:
                # Should not happen if current_tpm > 0, but as a safeguard.
                break
                
            oldest_timestamp, _ = tracker[0]
            now = datetime.now()
            
            # Calculate how long until the oldest entry expires from the 60s window
            time_since_oldest = (now - oldest_timestamp).total_seconds()
            sleep_duration = 60.1 - time_since_oldest # Sleep a bit extra to be safe
            
            if sleep_duration <= 0:
                # This can happen if pruning is slightly out of sync.
                # Just re-run the loop to get a fresh TPM count.
                continue

            await self.system.print(f':: pro-active TPM sleep for {user} on {device_path}: {sleep_duration}s')
            await asyncio.sleep(sleep_duration)

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
        io.login_time = datetime.now()
        io.banks = { } # A user's base context gets its own banks.
        io.log = Capture.log(self, join(self.USER_LOG, user), True)
        io.dev = device
        io.user = user
        io.su = device in (self.CONSOLE_DEV, '/dev/terminal') # if you have console, you're super
        io.base = True
        io.bot = device not in (self.CONSOLE_DEV, '/dev/terminal')
        self.users[user] = io

        # --- CWD and Home Directory Initialization ---
        if user == 'root':
            home_dir_virtual = '/root'
            home_dir_host = self.box(home_dir_virtual, io_context=io)
            
            if not os.path.exists(home_dir_host):
                # If /root does not exist on the host, set PWD to /
                io.pwd = '/'
                await io.print(f":: /root home directory not found. Setting PWD to /")
            else:
                # If /root exists on the host, set PWD to /root
                io.pwd = home_dir_virtual
                await io.print(f":: root home directory is {home_dir_virtual}")
            # Skip automatic creation and .skrc copying for root
        else:
            home_dir_virtual = f'/home/{user}'
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

        # Announce user login to network peers
        if self.port:
            await self.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'login',
                'user': user,
                'host': self.hostname
            })

        if interactive:
            await self.interactive(io)

        return io

    async def interactive(self, io):
        while not self.halt.is_set():
            start = datetime.now()
            try:
                # This outer try handles Ctrl+C when idle at the prompt
                try:
                    # Determine prompt character based on room status
                    if self.chat and self.chat.active_room:
                        prompt_char = '>>'
                    else:
                        prompt_char = '$'
                    
                    # Construct the prompt
                    prompt_str = f'[{io.user} {io.pwd}] {prompt_char} '

                    while (text := await io.input(prompt=prompt_str)) is None:
                        # non-blocking inputs return None until data
                        delay = (datetime.now() - start).total_seconds()
                        if delay < 0.1:
                            await asyncio.sleep(0.1 - delay)
                        start = datetime.now()

                    is_room_active = self.chat and self.chat.active_room

                    for line in text.split('\n'):
                        line = line.rstrip()
                        if not line:
                            continue
                        if line == '$ exit':
                            return
                        if line.startswith('#'):
                            continue

                        is_command = False
                        command_line = ''

                        if line.startswith('$ '):
                            is_command = True
                            command_line = line[2:]
                        elif not is_room_active:
                            # Not in a room, so treat as a command.
                            is_command = True
                            command_line = line
                        
                        if is_command:
                            if command_line:
                                io.history.append(command_line)
                            await self.call(io, command_line)
                        else:  # Is a chat message because we are in a room and not a command
                            if self.chat:
                                await self.chat.send(io.user, line)
                            else:
                                await io.print(line)

                except EOFError: # This handles Ctrl+D to log out
                    return

            except KeyboardInterrupt: # This handles Ctrl+C at the prompt
                # When Ctrl+C is pressed while idle, aioconsole raises KeyboardInterrupt.
                # We catch it, print a newline with ^C, and continue the loop to show a new prompt.
                await io.print("\n^C")
                continue

    async def logout(self, io:Context, disconnect=None):
        if io.user not in self.users:
            await self.system.error(f'!! not logged in: {io.user}')
            return False

        await self.system.print(f'IOSK logout: {io.user}')
        
        user_to_logout = io.user
        del self.users[user_to_logout]

        if disconnect:
            if self.chat: await self.chat.send(user_to_logout, disconnect, sys=True)
            else: await io.print(disconnect)

        # Announce user logout to network peers
        if self.port:
            await self.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'logout',
                'user': user_to_logout,
                'host': self.hostname
            })
        
        return True

    async def login_network_user(self, username, websocket):
        """Called by PortManager to log in a user from a network client."""
        await self.ready.wait()
        if self.halt.is_set(): return None

        if username in self.users:
            await self.system.error(f"!! login failed: user '{username}' already logged in.")
            return None
        
        device_path = f"network:{id(websocket)}"
        
        io = self.system.fork()
        io.login_time = datetime.now()
        io.banks = {}
        io.log = Capture.log(self, join(self.USER_LOG, username), True)
        io.dev = device_path
        io.user = username
        io.su = False
        io.base = True
        io.bot = False
        io.network_input_queue = asyncio.Queue()
        self.users[username] = io

        if username == 'root':
            home_dir_virtual = '/root'
            home_dir_host = self.box(home_dir_virtual, io_context=io)
            
            if not os.path.exists(home_dir_host):
                io.pwd = '/'
                await self.system.print(f":: Network root login: /root home directory not found. Setting PWD to /")
            else:
                io.pwd = home_dir_virtual
                await self.system.print(f":: Network root login: root home directory is {home_dir_virtual}")
        else:
            home_dir_virtual = f'/home/{username}'
            home_dir_host = self.box(home_dir_virtual, io_context=io)
            if not os.path.exists(home_dir_host):
                try:
                    os.makedirs(home_dir_host)
                    # For network users, output these messages to the system log, not their non-existent local console.
                    await self.system.print(f":: created home directory for network user {username}: {home_dir_virtual}")
                    skel_skrc_path = self.SKEL_SKRC
                    user_skrc_path = join(home_dir_virtual, '.skrc')
                    if await self.exists(io, skel_skrc_path):
                        await self.system.print(f":: copying {skel_skrc_path} to {user_skrc_path} for network user {username}")
                        await self.copy(io, skel_skrc_path, user_skrc_path)
                except Exception as e:
                    await self.system.error(f"!! failed to create home directory {home_dir_virtual} for network user {username}: {e}")
            io.pwd = home_dir_virtual
        
        skrc_global_path = self.SKRC
        if exists(self.box(skrc_global_path)):
            await self.exec(io, skrc_global_path)
        
        skrc_user_path = join('/home', username, '.skrc')
        if exists(self.box(skrc_user_path)):
            await self.exec(io, skrc_user_path)

        if self.port:
            await self.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'login',
                'user': username,
                'host': self.hostname
            })
        
        asyncio.create_task(self.interactive(io))
        
        return io

    async def logout_network_user(self, username):
        """Called by PortManager when a client disconnects."""
        if username in self.users:
            io = self.users[username]
            await self.logout(io, disconnect=f':: {username} has disconnected (network)')
    
    async def handle_client_input(self, username, data):
        """Called by PortManager to feed input to a network user's session."""
        if username in self.users:
            io = self.users[username]
            if hasattr(io, 'network_input_queue') and isinstance(io.network_input_queue, asyncio.Queue):
                await io.network_input_queue.put(data)

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
        if dev.startswith('network:'):
            if self.port:
                await self.port.send_to_client(io.user, data)
            return

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
        if dev.startswith('network:'):
            if prompt and self.port:
                await self.port.send_to_client(io.user, prompt)
            
            if hasattr(io, 'network_input_queue'):
                return await io.network_input_queue.get()
            else:
                await io.error("!! network user has no input queue.")
                raise EOFError

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

    async def get_device_client(self, io:Context, dev_virtual_path:str) -> object:
        """
        Gets a cached client instance for a device, or creates a new one.
        The client instance is cached using its virtual path as the key.
        """
        if dev_virtual_path in self.device_clients:
            return self.device_clients[dev_virtual_path]

        # Client not cached, so create it.
        # This requires a standardized way to get a client from a device module.
        dev_name = dev_virtual_path.replace('/dev/', '', 1)
        mod_name_for_pymod = dev_name.replace('/', '.')
        host_py_path = self.box(f"{dev_virtual_path}.py", io_context=io)
        dev_mod = self.pymod(f'dev.{mod_name_for_pymod}', host_py_path)

        if not dev_mod or not hasattr(dev_mod, 'get_client'):
            await io.error(f"!! device module for '{dev_virtual_path}' is invalid or missing get_client() function.")
            return None

        # Call the new standardized factory function in the device module.
        try:
            client = await dev_mod.get_client(io)
            if client:
                self.device_clients[dev_virtual_path] = client # Cache the new client
            return client
        except Exception as e:
            await io.error(f"!! failed to initialize client for '{dev_virtual_path}': {e}")
            return None

    ###
    ### TRACE
    ###

    async def is_trace_active(self, trace_name: str) -> bool:
        """Checks if a specific trace is active."""
        return self.trace_states.get(trace_name, False)

    async def log_trip_trace(self, io: Context, prompt: str, reply: str):
        """
        Logs token usage for TPM tracking. If 'trip' trace is active, also writes
        the prompt, reply, and token counts to log files.
        """
        # --- 1. Token Calculation (always needed for TPM) ---
        prompt_tokens = -1
        reply_tokens = -1
        reply_str = reply or ""
        try:
            encoding = tiktoken.get_encoding('cl100k_base')
            prompt_tokens = len(encoding.encode(prompt))
            reply_tokens = len(encoding.encode(reply_str))
        except Exception as e:
            # Silently fail on tiktoken error, tokens will be -1
            # A more robust system might log this, but for now we prioritize not crashing.
            pass

        # --- 2. TPM Tracking (always needed) ---
        try:
            total_tokens = (prompt_tokens if prompt_tokens != -1 else 0) + \
                           (reply_tokens if reply_tokens != -1 else 0)

            if total_tokens > 0:
                device_path = io.dev
                if device_path not in self.device_tpm_trackers:
                    self.device_tpm_trackers[device_path] = []
                
                self.device_tpm_trackers[device_path].append((datetime.now(), total_tokens))
                # Pruning of old entries is handled by _get_current_tpm before the next trip.
        except Exception as e:
            await self.system.error(f"!! Failed during TPM tracking for {io.dev}: {e}")

        # --- 3. Check for Active Trace ---
        if not await self.is_trace_active('trip'):
            return

        # --- 4. Write Trace Files ---
        try:
            # Filename Construction
            device_path = io.dev
            tid = self.device_trip_counters.get(device_path, 0) + 1
            self.device_trip_counters[device_path] = tid
            device_name = device_path.replace('/dev/', '').replace('/', '-')
            base_filename = f'{device_name}-{io.user}-{self.BOOT}-{io.cid}-{tid}'

            trip_log_dir_host = self.box('/var/log/trip')
            prompt_file_host = os.path.join(trip_log_dir_host, f'{base_filename}.prompt')
            reply_file_host = os.path.join(trip_log_dir_host, f'{base_filename}.reply')
            tokens_file_host = os.path.join(trip_log_dir_host, f'{base_filename}.tokens')

            # Token content string construction
            prompt_bytes = len(prompt.encode('utf-8'))
            reply_bytes = len(reply_str.encode('utf-8'))
            tokens_content = (
                f"PROMPT\n"
                f"Bytes: {prompt_bytes}\n"
                f"Tokens: {prompt_tokens if prompt_tokens != -1 else '(unavailable)'}\n\n"
                f"REPLY\n"
                f"Bytes: {reply_bytes}\n"
                f"Tokens: {reply_tokens if reply_tokens != -1 else '(unavailable)'}\n"
            )

            # Writing all trace files
            with open(prompt_file_host, 'w', encoding='utf-8') as f:
                f.write(prompt)
            with open(reply_file_host, 'w', encoding='utf-8') as f:
                f.write(reply_str)
            with open(tokens_file_host, 'w', encoding='utf-8') as f:
                f.write(tokens_content)
        except Exception as e:
            await self.system.error(f"!! Failed to write trip trace for {base_filename}: {e}")

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

