# sk/iosk/kernel.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture, UserSessionState, print_flush as print
from .parser import CommandLineParser
from .pipeline import CommandPipelineExecutor
from .chat import AIMessenger
from .port import PortManager
from . import util
from .fs import FileSystemManager
from .users import UserManager
from .proc import ProcessManager, Process

from binaryornot.check import is_binary
import tiktoken

import shlex
import asyncio
import aioconsole
from datetime import datetime, timedelta
import os
import posixpath
from os.path import isdir, isfile, exists, getsize, getmtime, abspath, dirname, join as path_join
import importlib, importlib.util, importlib.resources
import sys
import shutil
import traceback
from io import StringIO
import random
import re


class IOSK:
    BOOT = 0 # current boot number

    CONSOLE_DEV = '/dev/console'
    BOOT_COUNT = '/var/cache/boot'
    INIT_SCRIPT = '/sbin/init'
    SYSTEM_LOG = '/var/log/system'
    USER_LOG = '/var/log/user'
    SKRC = '/etc/skrc'
    SKEL_SKRC = '/etc/skel/skrc' # Added for the new requirement

    def __init__(self, workspace_root, mount_point=None):
        self.workspace_root = abspath(workspace_root)
        self.mount_point = mount_point
        self.system_workspace_root = None
        self.dist_root = None
        self.started = None

        if self.mount_point:
            # 3M mode: system state is in a hidden subdirectory.
            self.system_workspace_root = path_join(self.workspace_root, '.iosk')
        else:
            # Standard mode: system state is mixed with user files.
            self.system_workspace_root = self.workspace_root

        # --- Find Distribution Root ---
        try:
            # For installed packages via pip. This will find the bundled 'bin', 'etc', etc.
            self.dist_root = importlib.resources.files('sk').joinpath('iosk_dist')
        except (ModuleNotFoundError, AttributeError):
            # Fallback for development environment: the distribution is the workspace.
            # This allows direct editing of source files.
            self.dist_root = self.workspace_root

        # Handle the developer workflow case where workspace IS the distribution
        #if self.workspace_root == self.dist_root:
        #    print(":: Developer mode: Workspace and Distribution roots are the same.")

        self.ready = asyncio.Event()
        self.halt = asyncio.Event()

        self.system = None # Context
        
        # Managers for decomposed responsibilities
        self.fs = FileSystemManager(self)
        self.users = UserManager(self)
        self.proc = ProcessManager(self)
        # User contexts are now managed by UserManager
        # Process table is now managed by ProcessManager

        # Netroom subsystems
        self.port: PortManager = None
        self.chat: AIMessenger = None

        # Netroom state
        self.hostname: str = 'localhost'
        self.network_users: dict = {}
        self.network_rooms: dict = {}

        self.parser = CommandLineParser(self)
        self.pipeline_executor = CommandPipelineExecutor(self) # Instantiate the executor

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

        if not exists(self.workspace_root):
            try:
                os.makedirs(self.workspace_root)
                print(f":: Created workspace directory: {self.workspace_root}")
            except OSError as e:
                fail = f'bad workspace: could not create: {e}'
        elif not isdir(self.workspace_root):
            fail = f'bad workspace: not a directory: {self.workspace_root}'

        if not fail and self.mount_point:
            # In Mounted Media Mode, also ensure the system workspace (.iosk) exists.
            if not exists(self.system_workspace_root):
                try:
                    os.makedirs(self.system_workspace_root)
                except OSError as e:
                    fail = f'bad system workspace: could not create: {e}'
            elif not isdir(self.system_workspace_root):
                fail = f'bad system workspace: not a directory: {self.system_workspace_root}'

        io = None

        if not fail:
            # All filesystem operations now go through the overlay-aware fs manager
            # The fs manager will ensure writes go to the workspace
            boot_path_host = self.fs.box_for_write(self.BOOT_COUNT)
            
            # Ensure parent directory exists in workspace
            boot_dir = os.path.dirname(boot_path_host)
            if not exists(boot_dir):
                os.makedirs(boot_dir)

            if exists(boot_path_host):
                with open(boot_path_host, 'r') as bf:
                    self.BOOT = int(bf.read()) + 1
            
            with open(boot_path_host, 'w') as bf:
                bf.write(str(self.BOOT))
            
            # These directories are created in the workspace by fs write operations
            await self.fs.create_dir(Context(self, self.CONSOLE_DEV), f'{Context.CHATTER}/{self.BOOT}', parents=True)
            await self.fs.create_dir(Context(self, self.CONSOLE_DEV), Context.CODE, parents=True)
            await self.fs.create_dir(Context(self, self.CONSOLE_DEV), '/var/log/trip', parents=True)


        if not fail:
            io = self.system = Context(self, self.CONSOLE_DEV,
                                       Capture.log(self, self.SYSTEM_LOG, True))

            # The system context needs a session object to satisfy code
            # that expects io.session to exist (e.g., for aliases).
            self.system.session = UserSessionState()
            self.system.session.user = 'iosk'

            await io.print(f'IOSK boot number {self.BOOT}...')

        if not fail:
            # Read hostname
            hostname_path = self.fs.box('/etc/hostname')
            if await self.fs.exists(None, '/etc/hostname'):
                with open(hostname_path, 'r') as f:
                    self.hostname = f.read().strip() or 'localhost'
            else:
                self.hostname = os.path.basename(os.path.abspath(self.workspace_root)) or 'localhost'

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
        ok = await self.proc.exec(io, self.INIT_SCRIPT)
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

        for user, uio in self.users.contexts.copy().items():
            disconnect = f':: {user} has been disconnected (shutdown)'
            await self.users.logout(uio, disconnect=disconnect)

        # --- ADDED: Log system uptime on shutdown ---
        if self.started:
            uptime_td = datetime.now() - self.started
            days = uptime_td.days
            hours, remainder = divmod(uptime_td.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}d {hours:02d}h {minutes:02d}m {seconds:02d}s"
            await io.print(f':: System uptime was {uptime_str}.')

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
    ### USER LIFECYCLE (DELEGATED)
    ###

    async def get_motd(self, io: Context) -> str:
        """Gets the Message of the Day. Delegates to FileSystemManager."""
        return await self.fs.get_motd(io)

    async def run_post_login_setup(self, io: Context):
        """Runs startup scripts and other setup. Delegates to UserManager."""
        return await self.users.run_post_login_setup(io)

    async def login(self, user, device=None, interactive:bool=True,
                    connect=None, io_callback=None):
        """Log-in to get a Context. Delegates to UserManager."""
        return await self.users.login(user, device, interactive, connect, io_callback)

    async def interactive(self, io):
        """Runs the interactive user session loop. Delegates to UserManager."""
        return await self.users.interactive(io)

    async def logout(self, io:Context, disconnect=None):
        """Logs out a user. Delegates to UserManager."""
        return await self.users.logout(io, disconnect)

    async def broadcast_color_updates(self):
        """Triggers the PortManager to send color map updates to all clients."""
        if self.port:
            await self.port.broadcast_color_updates()

    async def login_network_user(self, username, websocket):
        """Logs in a network user. Delegates to UserManager."""
        return await self.users.login_network_user(username, websocket)

    async def logout_network_user(self, username):
        """Logs out a network user. Delegates to UserManager."""
        return await self.users.logout_network_user(username)

    async def handle_client_input(self, username, data):
        """Handles input from a network client. Delegates to UserManager."""
        return await self.users.handle_client_input(username, data)

    ###
    ### COMMAND (DELEGATED)
    ###

    async def call(self, io:Context, command_to_execute:str, original_line_for_history:str=None):
        """Interpret and execute a command pipeline. Delegates to ProcessManager."""
        return await self.proc.call(io, command_to_execute, original_line_for_history)

    async def execute_transient_command(self, base_io: Context, command_str: str, pwd: str) -> str:
        """Executes a command non-interactively. Delegates to ProcessManager."""
        return await self.proc.execute_transient_command(base_io, command_str, pwd)

    async def exec(self, io:Context, path:str, argv:list=None):
        """Executes a script with an interpreter. Delegates to ProcessManager."""
        return await self.proc.exec(io, path, argv)

    ###
    ### FILE OPS (DELEGATED)
    ###

    async def get_room_list(self, io: Context) -> list:
        """Lists all created rooms. Delegates to FileSystemManager."""
        return await self.fs.get_room_list(io)

    async def exists(self, io:Context, path:str):
        """Tests if a path exists, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            return await self.fs.exists(io, path)
        else:
            if not self.port:
                await io.error("!! netfs: network subsystem is not available.")
                return False
            return await self.port.remote_exists(hostname, virtual_path)

    async def create(self, io:Context, path:str):
        """Creates an empty file, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            return await self.fs.create(io, path)
        else:
            if not self.port:
                await io.error("!! netfs: network subsystem is not available.")
                return False
            # An empty put operation creates a file.
            return await self.port.remote_put_file(hostname, virtual_path, b'')

    async def copy(self, io:Context, from_path:str, to_path:str):
        """Copies a file, with support for local and remote paths."""
        from_host, from_vpath = self.parse_path(from_path)
        to_host, to_vpath = self.parse_path(to_path)

        is_from_local = not from_host or from_host == self.hostname
        is_to_local = not to_host or to_host == self.hostname

        # Case 1: Local -> Local (no changes, shutil.copy handles this)
        if is_from_local and is_to_local:
            return await self.fs.copy(io, from_path, to_path)

        if not self.port:
            await io.error("!! netfs: network subsystem is not available.")
            return False

        source_basename = posixpath.basename(from_vpath)

        # Case 2: Local -> Remote
        if is_from_local and not is_to_local:
            final_to_vpath = to_vpath
            # If remote destination ends with '/', treat it as a directory
            if to_vpath.endswith('/'):
                final_to_vpath = posixpath.join(to_vpath, source_basename)

            content_bytes = await self.get_raw(io, from_path)
            if content_bytes is None:
                return False
            return await self.port.remote_put_file(to_host, final_to_vpath, content_bytes)

        # Case 3: Remote -> Local
        if not is_from_local and is_to_local:
            final_to_path = to_path
            # For local destination, we can check if it's a directory
            host_dest_path = self.fs.box(to_path, io)
            if isdir(host_dest_path):
                final_to_path = posixpath.join(to_path, source_basename)

            content_bytes = await self.get_raw(io, from_path)
            if content_bytes is None:
                return False

            host_path = self.fs.box_for_write(final_to_path)
            try:
                parent_dir = dirname(host_path)
                if not exists(parent_dir):
                    os.makedirs(parent_dir, exist_ok=True)
                with open(host_path, 'wb') as f:
                    f.write(content_bytes)
                return True
            except Exception as e:
                await io.error(f"!! failed to write local file {final_to_path}: {e}")
                return False

        # Case 4: Remote -> Remote
        if not is_from_local and not is_to_local:
            final_to_vpath = to_vpath
            # Use the same heuristic for remote-to-remote copies
            if to_vpath.endswith('/'):
                final_to_vpath = posixpath.join(to_vpath, source_basename)

            # Case 4a: Same remote host
            if from_host == to_host:
                return await self.port.remote_copy(from_host, from_vpath, final_to_vpath)
            # Case 4b: Different remote hosts (third-party transfer via this host)
            else:
                await io.print(f":: proxying file from {from_host} to {to_host}...")
                content_bytes = await self.get_raw(io, from_path)
                if content_bytes is None:
                    return False
                return await self.port.remote_put_file(to_host, final_to_vpath, content_bytes)

        return False

    async def move(self, io:Context, from_path:str, to_path:str):
        """Moves a file or directory, with support for local and remote paths."""
        from_host, from_vpath = self.parse_path(from_path)
        to_host, to_vpath = self.parse_path(to_path)

        is_from_local = not from_host or from_host == self.hostname
        is_to_local = not to_host or to_host == self.hostname

        # Case 1: Local -> Local
        if is_from_local and is_to_local:
            return await self.fs.move(io, from_path, to_path)

        if not self.port:
            await io.error("!! netfs: network subsystem is not available.")
            return False

        # Optimization: Remote -> Remote on the same host
        if not is_from_local and not is_to_local and from_host == to_host:
            return await self.port.remote_move(from_host, from_vpath, to_vpath)

        # All other cases are emulated as copy then remove.
        copied = await self.copy(io, from_path, to_path)
        if not copied:
            await io.error(f"!! move failed: could not copy {from_path} to {to_path}")
            return False

        removed = await self.remove(io, from_path)
        if not removed:
            await io.error(f"!! move warning: source {from_path} could not be removed after copy.")
            return False

        return True

    async def remove(self, io:Context, path:str):
        """Removes a file, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            return await self.fs.remove(io, path)
        else:
            if not self.port:
                await io.error("!! netfs: network subsystem is not available.")
                return False
            return await self.port.remote_remove_file(hostname, virtual_path)

    async def create_dir(self, io:Context, path:str, parents=False):
        """Creates a directory, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            return await self.fs.create_dir(io, path, parents)
        else:
            if not self.port:
                await io.error("!! netfs: network subsystem is not available.")
                return False
            return await self.port.remote_create_dir(hostname, virtual_path, parents=parents)

    async def remove_dir(self, io:Context, path:str):
        """Removes a directory, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            return await self.fs.remove_dir(io, path)
        else:
            if not self.port:
                await io.error("!! netfs: network subsystem is not available.")
                return False
            return await self.port.remote_remove_dir(hostname, virtual_path)

    async def unremove(self, io:Context, path:str):
        """Restores a file by removing its tombstone. Delegates to FileSystemManager."""
        return await self.fs.unremove(io, path)

    async def list_dir(self, io: Context, path: str, recursive: bool = False, show_all: bool = False, honor_skignore: bool = True) -> list:
        """Lists directory contents, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            return await self.fs.list_dir(io, path, recursive=recursive, show_all=show_all, honor_skignore=honor_skignore)
        else:
            if not self.port:
                await io.error("!! netfs: network subsystem is not available.")
                return None
            return await self.port.remote_list_dir(hostname, virtual_path, recursive=recursive, show_all=show_all, honor_skignore=honor_skignore)

    ###
    ### FILE I/O (DELEGATED AND LOCAL)
    ###

    async def get(self, io:Context, path:str):
        """Gets file contents, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            return await self.fs.get(io, path) # Local case uses local logic with is_binary check
        else:
            # Remote case: get raw bytes and attempt to decode
            content_bytes = await self.get_raw(io, path)
            if content_bytes is None:
                return None
            try:
                # We can't do a proper is_binary check on remote bytes without the file.
                # The primary goal of `get` is to return decoded text, so we attempt that.
                # A binary file will fail here, which is the desired outcome.
                return content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                await io.error(f"!! remote file is not utf-8 encoded or is binary: {path}")
                return None

    async def get_raw(self, io:Context, path:str):
        """Gets raw file contents, locally or remotely."""
        hostname, virtual_path = self.parse_path(path)
        if not hostname or hostname == self.hostname:
            content, _, error = await self.fs.get_raw(io, path)
            if error:
                await io.error(f"!! get_raw failed for {path}: {error}")
                return None
            return content
        else:
            if not self.port:
                await io.error("!! netfs: network subsystem is not available.")
                return None
            return await self.port.remote_get_file(hostname, virtual_path)

    async def send(self, io:Context, dev:str, data):
        """Send data to device."""
        if dev.startswith('network:'):
            if self.port:
                if data.startswith('\a'):
                    try:
                        # DM format: \a\n[SENDER -> me TIMESTAMP] << CONTENT
                        lines = data.split('<<', 1)
                        header = lines[0]
                        content = lines[1].strip() if len(lines) > 1 else ""

                        # The ' -> ' part is not colored, making it a safe split point.
                        header_inside_brackets = header.split('[', 1)[1].rsplit(']', 1)[0]
                        sender_part, rest_of_header = header_inside_brackets.split(' -> ', 1)

                        # To verify, we strip ANSI codes from the part after ' -> '.
                        ansi_escape_pattern = re.compile(r'\x1b\[\d+m')
                        cleaned_rest = ansi_escape_pattern.sub('', rest_of_header.strip())

                        if cleaned_rest.startswith('me '):
                            from_user = sender_part.strip()
                        else:
                            raise ValueError("Could not confirm 'me' in DM header")

                        # Send structured DM payload to the client
                        await self.port.send_private_message_to_client(
                            to_user=io.session.user,
                            from_user=from_user,
                            content=content
                        )
                        # Also send the formatted message to the console for history.
                        # The bell is required to trigger sounds and fallbacks.
                        await self.port.send_to_client(io.session.user, data)
                        return # We are done with this data.

                    except Exception as e:
                        # If parsing fails for any reason, fall back to old behavior
                        # but log the error to the system log for debugging.
                        await self.system.error(f"!! DM parsing failed in kernel: {e}")
                        await self.port.send_to_client(io.session.user, data)
                        return
                else:
                    await self.port.send_to_client(io.session.user, data)
            return

        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return False

        dev = dev[5:]
        virtual_dev_path = posixpath.join('/dev', dev)
        path = self.fs.box(virtual_dev_path)
        py = await self.pymod(f'dev.{dev.replace("/", ".").replace("-", "_")}', path, virtual_path=virtual_dev_path)

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
                await self.port.send_prompt_to_client(io.session.user, prompt)

            if hasattr(io, 'network_input_queue'):
                return await io.network_input_queue.get()
            else:
                await io.error("!! network user has no input queue.")
                raise EOFError

        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return None

        dev = dev[5:]
        virtual_dev_path = posixpath.join('/dev', dev)
        path = self.fs.box(virtual_dev_path)
        py = await self.pymod(f'dev.{dev.replace("/", ".").replace("-", "_")}', path, virtual_path=virtual_dev_path)

        if py:
            try:
                return await py.iorecv(io, prompt=prompt)
            except EOFError:
                # EOFError is a signal for logout, it must be propagated up
                # to the interactive loop.
                raise
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
        mod_name_for_pymod = dev_name.replace('/', '.').replace('-', '_')
        # The original code explicitly looked for a .py file. We preserve this by checking
        # for existence of the logical path, which fs.exists will resolve to a .py file if needed.
        virtual_py_path = f"{dev_virtual_path}.py"
        host_py_path = self.fs.box(virtual_py_path, io_context=io)
        dev_mod = await self.pymod(f'dev.{mod_name_for_pymod}', host_py_path, virtual_path=dev_virtual_path)

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
    ### TOKEN TELEMETRY
    ###

    async def _calculate_context_tokens(self, io: Context) -> dict:
        """
        Calculates token and byte counts for the components of a user's context.
        This logic is extracted from 'tokens.py' for reuse in telemetry.
        """
        stats = {
            'banked_bytes': 0, 'banked_tokens': 0,
            'history_bytes': 0, 'history_tokens': 0,
            'caching_context_bytes': 0, 'caching_context_tokens': 0
        }
        encoding = None
        try:
            encoding = tiktoken.get_encoding('cl100k_base')
        except Exception:
            # If tiktoken fails, we can't calculate tokens, but can still do bytes.
            pass

        # --- 1. Preamble Content ---
        preamble_content = io.session.preamble_cache or ""

        # --- 2. Banked Memory Content ---
        raw_banking_content = ""
        if io.session.banks:
            for bank_acct, data in io.session.banks.items():
                raw_banking_content += '\n' + data + '\n'

        banking_content = ""
        if raw_banking_content:
            banking_content = (
                util.AI_MEM_HEADER +
                util.AI_MEM_PROMPT +
                f'{raw_banking_content}' +
                util.AI_MEM_FOOTER
            )

        stats['banked_bytes'] = len(banking_content.encode('utf-8'))
        if encoding:
            stats['banked_tokens'] = len(encoding.encode(banking_content))

        # --- 3. Chat History Content ---
        # --- History Proposal Implementation ---
        chat_history_content = io.get_session_string()
        # io.session.seek(0) # REPLACED
        # chat_history_content = io.session.read() # REPLACED
        # --- End Implementation ---
        stats['history_bytes'] = len(chat_history_content.encode('utf-8'))
        if encoding:
            stats['history_tokens'] = len(encoding.encode(chat_history_content))

        # --- 4. Caching Context (Preamble + Banked + History) ---
        caching_context_content = preamble_content + banking_content + chat_history_content
        stats['caching_context_bytes'] = len(caching_context_content.encode('utf-8'))
        if encoding:
            stats['caching_context_tokens'] = len(encoding.encode(caching_context_content))

        return stats

    ###
    ### TRACE
    ###

    async def is_trace_active(self, trace_name: str) -> bool:
        """Checks if a specific trace is active."""
        return self.trace_states.get(trace_name, False)

    async def log_trip_trace(self, io: Context, prompt: str, reply: str):
        """
        Logs token usage for TPM tracking and real-time telemetry. If 'trip' trace
        is active, also writes the prompt, reply, and token counts to log files.
        """
        # --- 1. Token Calculation for Telemetry and TPM ---
        prompt_tokens = -1
        reply_tokens = -1
        reply_str = reply or ""
        prompt_bytes = len(prompt.encode('utf-8'))
        reply_bytes = len(reply_str.encode('utf-8'))

        try:
            encoding = tiktoken.get_encoding('cl100k_base')
            prompt_tokens = len(encoding.encode(prompt))
            reply_tokens = len(encoding.encode(reply_str))
        except Exception as e:
            # Silently fail on tiktoken error, tokens will be -1.
            pass

        # --- 2. Update Bot Telemetry Stats ---
        if io.session.bot:
            # First, calculate the state of the context that was just used for the trip.
            context_stats = await self._calculate_context_tokens(io)
            io.session.token_stats.update(context_stats)

            # Update last trip stats
            io.session.token_stats['last_trip_input_bytes'] = prompt_bytes
            io.session.token_stats['last_trip_input_tokens'] = prompt_tokens if prompt_tokens != -1 else 0
            io.session.token_stats['last_trip_output_bytes'] = reply_bytes
            io.session.token_stats['last_trip_output_tokens'] = reply_tokens if reply_tokens != -1 else 0

            # Increment cumulative stats
            io.session.token_stats['cumulative_input_bytes'] += prompt_bytes
            if prompt_tokens != -1:
                io.session.token_stats['cumulative_input_tokens'] += prompt_tokens
            io.session.token_stats['cumulative_output_bytes'] += reply_bytes
            if reply_tokens != -1:
                io.session.token_stats['cumulative_output_tokens'] += reply_tokens
            
            # Broadcast the update to clients
            if self.port:
                await self.port.broadcast_token_stats_update(io)

        # --- 3. TPM Tracking (always needed) ---
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

        # --- 4. Check for Active Trace ---
        if not await self.is_trace_active('trip'):
            return

        # --- 5. Write Trace Files ---
        try:
            # Filename Construction
            device_path = io.dev
            tid = self.device_trip_counters.get(device_path, 0) + 1
            self.device_trip_counters[device_path] = tid
            device_name = device_path.replace('/dev/', '').replace('/', '-')
            base_filename = f'{device_name}-{io.session.user}-{self.BOOT}-{io.cid}-{tid}'

            trip_log_dir_host = self.fs.box_for_write('/var/log/trip')
            prompt_file_host = os.path.join(trip_log_dir_host, f'{base_filename}.prompt')
            reply_file_host = os.path.join(trip_log_dir_host, f'{base_filename}.reply')
            tokens_file_host = os.path.join(trip_log_dir_host, f'{base_filename}.tokens')

            # Token content string construction
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
        """Sandboxes a virtual path to the host. Delegates to FileSystemManager."""
        return self.fs.box(virtual_path_input, io_context)

    def parse_path(self, path_str: str) -> tuple[str | None, str]:
        """
        Parses a path string into (hostname, virtual_path).
        Returns (None, path_str) if the path is local.
        Syntax: `hostname:/path/to/resource`
        """
        if ':' in path_str:
            hostname, virtual_path = path_str.split(':', 1)
            # A valid remote path must have a non-empty hostname and start with a '/'
            if hostname and virtual_path.startswith('/'):
                return hostname, virtual_path
        return None, path_str

    async def pymod(self, modname, path, virtual_path=None):
        """Import python module at path as the given module name."""
        # Requirement 4: Honor tombstones by checking existence with fs.exists
        if virtual_path and not await self.fs.exists(None, virtual_path):
            return None

        modname = f'sk.iosk.{modname}'
        if not path.endswith('.py'): path += '.py'

        py = None
        try:
            spec = importlib.util.spec_from_file_location(modname, path)
            if spec and spec.loader:
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