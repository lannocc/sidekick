# sk/iosk/kernel.py
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
import posixpath
from os.path import isdir, isfile, exists, getsize, getmtime
import importlib, importlib.util
import sys
import shutil
import traceback
from io import StringIO
import random
import re


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

    ANSI_RESET = '\033[0m'
    ANSI_BOLD = '\033[1m'
    BRIGHT_WHITE = '\033[97m'
    USER_COLORS = [
        '\033[96m',  # Bright Cyan
        '\033[92m',  # Bright Green
        '\033[93m',  # Bright Yellow
        '\033[94m',  # Bright Blue
        '\033[95m',  # Bright Magenta
        '\033[91m',  # Bright Red
    ]

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

    def _get_next_color(self, io: Context) -> str:
        """Cycles through the USER_COLORS list to pick a color."""
        color = self.USER_COLORS[io.color_idx % len(self.USER_COLORS)]
        io.color_idx += 1
        return color

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

            chatter = self.box(f'{Context.CHATTER}/{self.BOOT}')
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
    ### USER LIFECYCLE
    ###

    async def get_motd(self, io: Context) -> str:
        """
        Gets the Message of the Day.
        If /etc/motd is a file, returns its content.
        If /etc/motd is a directory, returns the content of a randomly selected file from it.
        """
        motd_path_virtual = '/etc/motd'
        motd_path_host = self.box(motd_path_virtual, io_context=io)

        if not await self.exists(io, motd_path_virtual):
            return ""  # No MOTD found

        if isdir(motd_path_host):
            try:
                # Use kernel's list_dir to get contents
                dir_contents = await self.list_dir(io, motd_path_virtual)

                # Filter for files only
                files = [item['name'] for item in dir_contents if item['type'] == 'file']

                if not files:
                    return ""  # Directory is empty

                random_motd_filename = random.choice(files)
                random_motd_path_virtual = posixpath.join(motd_path_virtual, random_motd_filename)

                # Now, use self.get() to read the file content.
                content = await self.get(io, random_motd_path_virtual)
                return content or ""

            except Exception as e:
                await self.system.error(f"!! Error reading MOTD from directory {motd_path_virtual}: {e}")
                traceback.print_exc()
                return ""

        elif isfile(motd_path_host):
            # It's a file, use self.get() as before.
            content = await self.get(io, motd_path_virtual)
            return content or ""

        else:
            # It exists but is not a file or directory.
            return ""

    async def run_post_login_setup(self, io: Context):
        """Runs startup scripts and other setup after a user is fully logged in."""
        if not io or not io.user:
            return

        # Display MOTD if not joining a room.
        # This mirrors the logic for network clients in port.py.
        if not (self.chat and self.chat.active_room):
            motd_content = getattr(io, 'motd_cache', None)
            if motd_content:
                await io.print(motd_content)

        # Execute system-wide skrc
        skrc_global_path = self.SKRC
        if exists(self.box(skrc_global_path)):
            await self.exec(io, skrc_global_path)

        # Execute user-specific .skrc
        # The user's PWD is set to their home directory (e.g., /root, /home/user)
        # So we can construct the .skrc path relative to PWD.
        skrc_user_path = posixpath.join(io.pwd, '.skrc')
        if await self.exists(io, skrc_user_path): # Use self.exists as it handles virtual paths properly
            await self.exec(io, skrc_user_path)

        if self.chat and self.chat.active_room:
            await self.chat.add_to_room(io)

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

        login_msg = f":: user '{user}' logged in on '{self.hostname}'"
        await self.system.print(login_msg)

        io = self.system.fork()
        io.login_time = datetime.now()
        io.banks = { } # A user's base context gets its own banks.
        io.history = [] # A user's base context gets its own history.
        # --- BEGIN FIX ---
        # A new user's base context must have its own session history to prevent
        # inheriting and sharing history with the system context or other users.
        io.session_history = []
        io.prompt_number = 1
        # --- END FIX ---
        io.log = Capture.log(self, f'{self.USER_LOG}/{user}', True)
        io.dev = device
        io.user = user
        io.su = device == self.CONSOLE_DEV # if you have console, you're super
        io.base = True
        io.bot = device != self.CONSOLE_DEV
        self.users[user] = io

        user_addr = f"{user}.{self.hostname}"

        # --- Color Initialization ---
        # Part 1: If the new user is interactive, set up THEIR color map.
        # Bots do not need their own color map as they don't "see" colors.
        if not io.bot:
            # This user is interactive, set up their color map with user.host keys.
            # 1a. Assign self-color (white)
            io.user_colors[user_addr] = self.BRIGHT_WHITE

            # 1b. Populate this new user's map with all other known users.
            all_other_users = list(self.network_users.keys())
            for u, uio in self.users.items():
                # self.users already contains the new user, so we must skip them.
                if u != user:
                    all_other_users.append(f"{u}.{self.hostname}")

            for other_addr in all_other_users:
                 io.user_colors[other_addr] = self._get_next_color(io)

        # Part 2: Add the new user (bot or not) to all existing interactive users' maps.
        # This allows interactive users to see and set colors for bots.
        for other_io in self.users.values():
            if other_io.user != user and not other_io.bot:
                other_io.user_colors[user_addr] = self._get_next_color(other_io)

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
                    user_skrc_path = posixpath.join(home_dir_virtual, '.skrc')
                    if await self.exists(io, skel_skrc_path):
                        await io.print(f":: copying {skel_skrc_path} to {user_skrc_path}")
                        await self.copy(io, skel_skrc_path, user_skrc_path)

                except Exception as e:
                    await self.system.error(f"!! failed to create home directory {home_dir_virtual}: {e}")
                    # For now, allow login to proceed but log the error.
            io.pwd = home_dir_virtual # Set the current working directory for the user

        # Determine and cache the MOTD for this session to ensure consistency.
        io.motd_cache = await self.get_motd(io)

        if io_callback:
            await io_callback(io)

        if connect:
            if self.chat: await self.chat.send(user, connect, sys=True)
            else: await io.print(connect)

        # MODIFIED: Update local network_users and then broadcast
        self.network_users[user_addr] = {'is_bot': io.bot, 'paused': io.paused}

        # Announce user login to network peers
        if self.port:
            await self.port.broadcast_color_updates()
            await self.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'login',
                'user': user,
                'host': self.hostname,
                'is_bot': io.bot,
                'paused': io.paused
            })
            # Announce user login to the entire mesh system log
            await self.port.broadcast_to_peers({
                'type': 'system_broadcast',
                'message': login_msg
            })

        # For local logins, run post-setup immediately.
        await self.run_post_login_setup(io)

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

                    # --- History Proposal Implementation ---
                    # Construct the prompt with the new prompt number and format.
                    prompt_str = f'[{io.user} #{io.prompt_number} {io.pwd}] {prompt_char} '
                    # --- End Implementation ---

                    while (text := await io.input(prompt=prompt_str)) is None:
                        # non-blocking inputs return None until data
                        delay = (datetime.now() - start).total_seconds()
                        if delay < 0.1:
                            await asyncio.sleep(0.1 - delay)
                        start = datetime.now()

                    is_room_active = self.chat and self.chat.active_room

                    for line in text.split('\n'):
                        line = line.rstrip()
                        if not line or line.startswith('#'):
                            continue

                        is_command = False
                        command_to_run = ''
                        # The original line as typed by the user, for history purposes.
                        original_command_line = line

                        if line.startswith('$ '):
                            is_command = True
                            command_to_run = line[2:]
                        elif not is_room_active:
                            # Not in a room, so treat as a command.
                            is_command = True
                            command_to_run = line

                        if is_command:
                            # Check for built-in exit commands before executing.
                            # This is now the sole place `exit` is handled.
                            first_word = command_to_run.strip().split(' ', 1)[0]
                            if first_word in ('exit', 'logout'):
                                await self.logout(io)
                                return 'logout' # Return reason for exit

                            # The `history` command uses io.history. We must store the original line.
                            if command_to_run:
                                io.history.append(original_command_line)

                            # The `call` function handles adding the command and output
                            # to the AI's session_history. We pass it the command to execute
                            # and the original line for accurate logging.
                            await self.call(io, command_to_run, original_command_line)
                        else:   # Is a chat message because we are in a room and not a command.
                            if self.chat:
                                # The chat system is responsible for creating history entries
                                # and displaying the message for all participants (including the sender).
                                await self.chat.send(io.user, line)
                            else:
                                await io.print(line)

                except EOFError: # This handles Ctrl+D to log out
                    await self.logout(io)
                    return 'eof' # Return reason for exit

            except KeyboardInterrupt: # This handles Ctrl+C at the prompt
                # When Ctrl+C is pressed while idle, aioconsole raises KeyboardInterrupt.
                # We catch it, print a newline with ^C, and continue the loop to show a new prompt.
                #await io.print("\n^C")
                continue

    async def logout(self, io:Context, disconnect=None):
        if io.user not in self.users:
            await self.system.error(f'!! not logged in: {io.user}')
            return False

        logout_msg = f":: user '{io.user}' logged off from '{self.hostname}'"
        await self.system.print(logout_msg)

        user_to_logout = io.user
        user_addr_to_logout = f"{user_to_logout}.{self.hostname}"
        user_is_network_client = io.dev.startswith('network:')
        del self.users[user_to_logout]

        # --- Color Cleanup ---
        for remaining_io in self.users.values():
            if not remaining_io.bot and user_addr_to_logout in remaining_io.user_colors:
                del remaining_io.user_colors[user_addr_to_logout]

        if disconnect:
            if self.chat: await self.chat.send(user_to_logout, disconnect, sys=True)
            else: await io.print(disconnect)

        # MODIFIED: Update local network_users and then broadcast
        if user_addr_to_logout in self.network_users:
            del self.network_users[user_addr_to_logout]

        # Announce user logout to network peers
        if self.port:
            await self.port.broadcast_color_updates()
            await self.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'logout',
                'user': user_to_logout,
                'host': self.hostname
            })
            # Announce user logout to the entire mesh system log
            await self.port.broadcast_to_peers({
                'type': 'system_broadcast',
                'message': logout_msg
            })
            # If the user was a network client, close their connection
            if user_is_network_client:
                await self.port.disconnect_client(user_to_logout)

        return True

    async def broadcast_color_updates(self):
        """Triggers the PortManager to send color map updates to all clients."""
        if self.port:
            await self.port.broadcast_color_updates()

    async def login_network_user(self, username, websocket):
        """Called by PortManager to log in a user from a network client."""
        await self.ready.wait()
        if self.halt.is_set(): return None

        if username in self.users:
            await self.system.error(f"!! login failed: user '{username}' already logged in.")
            return None

        login_msg = f":: user '{username}' logged in on '{self.hostname}' (client)"
        await self.system.print(login_msg)

        device_path = f"network:{id(websocket)}"

        io = self.system.fork()
        io.login_time = datetime.now()
        io.banks = {}
        io.history = [] # A network user's base context gets its own history.
        # --- BEGIN FIX ---
        # A new network user's base context must also have its own session history
        # to ensure isolation from other users.
        io.session_history = []
        io.prompt_number = 1
        # --- END FIX ---
        io.log = Capture.log(self, f'{self.USER_LOG}/{username}', True)
        io.dev = device_path
        io.user = username
        io.su = False
        io.base = True
        io.bot = False
        io.network_input_queue = asyncio.Queue()
        self.users[username] = io

        user_addr = f"{username}.{self.hostname}"

        # --- Color Initialization (for network user) ---
        # Part 1: If the new user is interactive, set up THEIR color map.
        if not io.bot:
            # This user is interactive, set up their color map with user.host keys.
            # 1a. Assign self-color (white)
            io.user_colors[user_addr] = self.BRIGHT_WHITE

            # 1b. Populate this new user's map with all other known users.
            all_other_users = list(self.network_users.keys())
            for u, uio in self.users.items():
                if u != username:
                    all_other_users.append(f"{u}.{self.hostname}")

            for other_addr in all_other_users:
                 io.user_colors[other_addr] = self._get_next_color(io)

        # Part 2: Add the new user (bot or not) to all existing interactive users' maps.
        for other_io in self.users.values():
            if other_io.user != username and not other_io.bot:
                other_io.user_colors[user_addr] = self._get_next_color(other_io)

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
                    user_skrc_path = posixpath.join(home_dir_virtual, '.skrc')
                    if await self.exists(io, skel_skrc_path):
                        await self.system.print(f":: copying {skel_skrc_path} to {user_skrc_path} for network user {username}")
                        await self.copy(io, skel_skrc_path, user_skrc_path)
                except Exception as e:
                    await self.system.error(f"!! failed to create home directory {home_dir_virtual} for network user {username}: {e}")
            io.pwd = home_dir_virtual

        # Determine and cache the MOTD for this session to ensure consistency.
        io.motd_cache = await self.get_motd(io)

        # MODIFIED: Update local network_users and then broadcast
        self.network_users[user_addr] = {'is_bot': io.bot, 'paused': io.paused}

        if self.port:
            await self.port.broadcast_color_updates()
            await self.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'login',
                'user': username,
                'host': self.hostname,
                'is_bot': io.bot,
                'paused': io.paused
            })
            await self.port.broadcast_to_peers({
                'type': 'system_broadcast',
                'message': login_msg
            })

        # Do not run post-login setup here. The PortManager will do it.
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

    async def call(self, io:Context, command_to_execute:str, original_line_for_history:str=None):
        """Interpret arguments, parse for pipes/redirection, and invoke commands."""
        # If original_line_for_history is not provided, it's a non-interactive call.
        # Use the command itself for the history line; it will be filtered by `io.base` anyway.
        history_line = original_line_for_history if original_line_for_history is not None else command_to_execute
        # Delegate the entire pipeline execution to the CommandPipelineExecutor
        return await self.pipeline_executor.execute_pipeline(io, command_to_execute, history_line, self.parser)

    async def execute_transient_command(self, base_io: Context, command_str: str, pwd: str) -> str:
        """
        Executes a command in a temporary, non-interactive context and captures its output.
        Used for features like 'watch'.
        """
        if not await self.exists(base_io, pwd):
            return f"watch error: directory not found: {pwd}"
            
        temp_io = base_io.fork()
        temp_io.base = False  # Mark as a non-base, transient session
        temp_io.dev = '/dev/null' # Does not have a real device
        temp_io.pwd = pwd

        # Redirect stdout and stderr to a string buffer
        output_capture = StringIO()
        temp_io.stdout = output_capture
        temp_io.stderr = output_capture

        try:
            # Execute the command pipeline
            await self.call(temp_io, command_str)
        except Exception as e:
            # Capture exceptions during command parsing/execution as well
            traceback.print_exc(file=output_capture)

        return output_capture.getvalue()

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
                script_and_args_for_interpreter = [path] + argv

                # --- BEGIN FIX ---
                # The original code called `self.call`, creating a potential infinite recursion
                # if a script specified itself as its interpreter. The fix is to directly
                # resolve the interpreter as a Python module and execute its `iocall` method,
                # bypassing the main `call` pathway. This breaks the recursive loop.

                # We resolve the interpreter path and check if it's a valid Python module.
                # This logic is a simplified version of what's in `pipeline.py`.
                interpreter_path = posixpath.join('/bin', interpreter)
                sandboxed_py_path = self.box(f'{interpreter_path}.py', io_context=io)

                if exists(sandboxed_py_path) and isfile(sandboxed_py_path):
                    try:
                        modname_for_pymod = interpreter_path.strip("/").replace("/", ".").replace("-", "_")
                        py_mod = self.pymod(modname_for_pymod, sandboxed_py_path)
                        if py_mod and hasattr(py_mod, 'iocall'):
                            # Execute the interpreter's iocall method directly.
                            return await py_mod.iocall(io, script_and_args_for_interpreter)
                        else:
                            await io.error(f"!! interpreter '{interpreter}' is not a valid module with iocall.")
                            return False
                    except Exception as e:
                        await io.error(f"!! exception calling interpreter '{interpreter}': {e}")
                        traceback.print_exc()
                        return False
                else:
                    await io.error(f"!! interpreter not found or not a Python module: {interpreter_path}.py")
                    return False
                # --- END FIX ---

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

    async def get_room_list(self, io: Context) -> list:
        """
        Lists all created rooms on the local system.
        Returns a list of dictionaries, each with 'name' and 'topic'.
        """
        room_dir_virtual = '/var/room'
        room_dir_host = self.box(room_dir_virtual, io_context=io)

        if not exists(room_dir_host) or not isdir(room_dir_host):
            return []

        try:
            room_names = sorted([
                name for name in os.listdir(room_dir_host)
                if isdir(os.path.join(room_dir_host, name))
            ])
        except OSError:
            return []

        room_data = []
        for name in room_names:
            topic_path = posixpath.join(room_dir_virtual, name, 'topic')
            topic = ""
            if await self.exists(io, topic_path):
                 topic_content = await self.get(io, topic_path)
                 if topic_content:
                     topic = topic_content.strip()
            room_data.append({'name': name, 'topic': topic})

        return room_data

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
            virtual_path = posixpath.normpath(posixpath.join(io.pwd, path))
        else:
            virtual_path = posixpath.normpath(path)

        # Convert virtual path to module path suffix, e.g., '/dev/google' -> 'dev.google'
        mod_suffix = virtual_path.lstrip('/')
        if not mod_suffix:
            return False # Path was just '/'

        # The convention is to find modules relative to the 'iosk' package.
        # Example: /dev/google -> dev.google -> iosk.dev.google
        full_mod_name = f'iosk.{mod_suffix.replace("/", ".").replace("-", "_")}'

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

    async def list_dir(self, io: Context, path: str, recursive: bool = False) -> list:
        """Lists the contents of a directory in the sandbox, optionally recursively."""
        host_path = self.box(path, io_context=io)
        if not exists(host_path):
            raise FileNotFoundError(f"Path not found: {path}")
        if not isdir(host_path):
            raise NotADirectoryError(f"Path is not a directory: {path}")

        listing = []
        try:
            if recursive:
                for root, dirs, files in os.walk(host_path, topdown=True):
                    # Sort dirs and files to ensure consistent output
                    dirs.sort()
                    files.sort()
                    # Convert host root path back to virtual path for this level
                    relative_path_from_start = os.path.relpath(root, host_path)
                    if relative_path_from_start == '.':
                        virtual_root = path
                    else:
                        # Ensure we use POSIX separators for the virtual path
                        virtual_root = posixpath.join(path, *relative_path_from_start.split(os.sep))

                    # Process all files at the current level
                    for item_name in files:
                        item_host_path = os.path.join(root, item_name)
                        item_virtual_path = posixpath.join(virtual_root, item_name)
                        try:
                            size = getsize(item_host_path)
                            mtime = getmtime(item_host_path)
                        except OSError:
                            size = -1
                            mtime = -1
                        listing.append({'name': item_name, 'path': item_virtual_path, 'type': 'file', 'size': size, 'mtime': mtime})

                    # Process all subdirectories at the current level
                    for item_name in dirs:
                        item_host_path = os.path.join(root, item_name)
                        item_virtual_path = posixpath.join(virtual_root, item_name)
                        try:
                            size = getsize(item_host_path)
                            mtime = getmtime(item_host_path)
                        except OSError:
                            size = -1
                            mtime = -1
                        listing.append({'name': item_name, 'path': item_virtual_path, 'type': 'dir', 'size': size, 'mtime': mtime})
            else:
                for item_name in sorted(os.listdir(host_path)):
                    full_item_path_host = os.path.join(host_path, item_name)
                    full_item_path_virtual = posixpath.join(path, item_name)
                    item_type = 'dir' if isdir(full_item_path_host) else 'file'
                    try:
                        size = getsize(full_item_path_host)
                        mtime = getmtime(full_item_path_host)
                    except OSError:
                        size = -1
                        mtime = -1
                    listing.append({
                        'name': item_name,
                        'path': full_item_path_virtual,
                        'type': item_type,
                        'size': size,
                        'mtime': mtime
                    })
        except OSError as e:
            await io.error(f"Error reading directory {path}: {e}")
            raise
        return listing

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

    async def get_raw(self, io:Context, path:str):
        """Get raw file contents as bytes, and determine if it's binary."""
        file = self.box(path, io_context=io)
        if not exists(file):
            error_msg = f'path not found: {path}'
            return None, False, error_msg

        if not isfile(file):
            error_msg = f'not a file: {path}'
            return None, False, error_msg
        
        try:
            is_binary_file = is_binary(file)
            with open(file, 'rb') as f:
                content = f.read()
            return content, is_binary_file, None
        except Exception as e:
            error_msg = f'could not read file: {e}'
            return None, False, error_msg

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
                            to_user=io.user,
                            from_user=from_user,
                            content=content
                        )
                        # Also send the formatted message to the console for history.
                        # The bell is required to trigger sounds and fallbacks.
                        await self.port.send_to_client(io.user, data)
                        return # We are done with this data.

                    except Exception as e:
                        # If parsing fails for any reason, fall back to old behavior
                        # but log the error to the system log for debugging.
                        await self.system.error(f"!! DM parsing failed in kernel: {e}")
                        await self.port.send_to_client(io.user, data)
                        return
                else:
                    await self.port.send_to_client(io.user, data)
            return

        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return False

        dev = dev[5:]
        path = self.box(posixpath.join('/dev', dev))
        py = self.pymod(f'dev.{dev.replace("/", ".").replace("-", "_")}', path)

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
                await self.port.send_prompt_to_client(io.user, prompt)

            if hasattr(io, 'network_input_queue'):
                return await io.network_input_queue.get()
            else:
                await io.error("!! network user has no input queue.")
                raise EOFError

        if not dev.startswith('/dev/'):
            await io.error(f'!! not a device: {dev}')
            return None

        dev = dev[5:]
        path = self.box(posixpath.join('/dev', dev))
        py = self.pymod(f'dev.{dev.replace("/", ".").replace("-", "_")}', path)

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
        preamble_content = io.preamble_cache or ""

        # --- 2. Banked Memory Content ---
        raw_banking_content = ""
        if io.banks:
            for bank_acct, data in io.banks.items():
                raw_banking_content += '\n' + data + '\n'

        banking_content = ""
        if raw_banking_content:
            banking_content = (
                '\n=== CORE RULES/MEMORY BEGIN ===\n'
                'THIS SECTION IS MOST IMPORTANT, I MUST ALWAYS REMEMBER:\n'
                f'{raw_banking_content}'
                '\n=== END   CORE RULES/MEMORY ===\n'
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
        if io.bot:
            # First, calculate the state of the context that was just used for the trip.
            context_stats = await self._calculate_context_tokens(io)
            io.token_stats.update(context_stats)

            # Update last trip stats
            io.token_stats['last_trip_input_bytes'] = prompt_bytes
            io.token_stats['last_trip_input_tokens'] = prompt_tokens if prompt_tokens != -1 else 0
            io.token_stats['last_trip_output_bytes'] = reply_bytes
            io.token_stats['last_trip_output_tokens'] = reply_tokens if reply_tokens != -1 else 0

            # Increment cumulative stats
            io.token_stats['cumulative_input_bytes'] += prompt_bytes
            if prompt_tokens != -1:
                io.token_stats['cumulative_input_tokens'] += prompt_tokens
            io.token_stats['cumulative_output_bytes'] += reply_bytes
            if reply_tokens != -1:
                io.token_stats['cumulative_output_tokens'] += reply_tokens
            
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
            base_filename = f'{device_name}-{io.user}-{self.BOOT}-{io.cid}-{tid}'

            trip_log_dir_host = self.box('/var/log/trip')
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
        """
        Sandboxes a given virtual path to the host filesystem, handling OS-specific separators.
        If io_context is provided and the path is relative, it resolves it relative to io_context.pwd.
        Returns the absolute host filesystem path.
        """
        # Step 1: Determine the effective virtual path using posixpath for virtual FS logic.
        effective_virtual_path = virtual_path_input
        if io_context and io_context.pwd and not posixpath.isabs(virtual_path_input):
            # Path is relative, resolve it against the current working directory.
            effective_virtual_path = posixpath.join(io_context.pwd, virtual_path_input)

        # Step 2: Normalize the virtual path to handle '.', '..', and multiple slashes using posixpath.
        normalized_virtual_path = posixpath.normpath(effective_virtual_path)

        # Step 3: Convert the virtual path to a host path.
        # Strip the leading '/' from the virtual path for os.path.join.
        path_relative_to_virtual_root = normalized_virtual_path.lstrip('/')

        # Split the sanitized virtual path by its separator '/' and join the components
        # to the host root path using the host OS's native separator via os.path.join.
        # This is the bridge between the virtual (posix) and host filesystems.
        path_components = path_relative_to_virtual_root.split('/')
        host_path = os.path.join(self.root, *path_components)

        # Return the absolute path on the host filesystem for consistency.
        return os.path.abspath(host_path)

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