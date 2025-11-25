# sk/iosk/users.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import Context, Capture, UserSessionState
from . import util

import asyncio
from datetime import datetime
import os
import posixpath
from os.path import exists


class UserManager:
    """Manages the user lifecycle for the IOSK kernel, including login, logout, and interactive sessions."""
    USER_COLORS = [
        util.COLOR_MAP['bright_cyan'],
        util.COLOR_MAP['bright_green'],
        util.COLOR_MAP['bright_yellow'],
        util.COLOR_MAP['bright_blue'],
        util.COLOR_MAP['bright_magenta'],
        util.COLOR_MAP['bright_red'],
    ]

    def __init__(self, kernel):
        self.os = kernel
        self.contexts = {} # handle:Context

    def _get_next_color(self, io: Context) -> str:
        """Cycles through the USER_COLORS list to pick a color."""
        color = self.USER_COLORS[io.session.color_idx % len(self.USER_COLORS)]
        io.session.color_idx += 1
        return color
    
    async def set_user_pause_state(self, io: Context, target_user: str, paused: bool):
        """Sets the paused state for a user and broadcasts the change."""
        target_io = self.contexts.get(target_user)
        if not target_io:
            # This should be validated by the caller, but as a safeguard.
            await io.error(f"!! set_user_pause_state: user '{target_user}' not found.")
            return False

        verb = "paused" if paused else "unpaused"
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Set the state
        target_io.session.paused = paused

        # Broadcast the state change to network peers
        if self.os.port:
            await self.os.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'state_update',
                'user': target_user,
                'host': self.os.hostname,
                'paused': paused
            })

        # Broadcast the state change to local clients
        if self.os.chat:
            await self.os.chat._broadcast_room_state_update()

        # Generate and send confirmations
        confirmation_message = f":: user '{target_user}' has been {verb} at {current_time}."
        await io.print(confirmation_message)

        # Inform the target user. If unpausing, always inform. If pausing, only
        # inform if another user is performing the action.
        if not paused or io.session.user != target_user:
             await target_io.print(confirmation_message)

        # Log to system log
        await self.os.system.print(f":: {io.session.user} {verb} user '{target_user}'")

        return True

    def _initialize_user_context(self, user: str, device: str) -> Context:
        """Creates and initializes a new user context object and its session state."""
        io = self.os.system.fork()
        session = UserSessionState()
        io.session = session

        # Populate session state
        session.login_time = datetime.now()
        session.user = user

        # Common per-context attributes
        io.base = True
        io.dev = device
        io.log = Capture.log(self.os, f'{self.os.USER_LOG}/{user}', True)

        # Type-specific session attributes
        is_console_user = (device == self.os.CONSOLE_DEV)
        is_network_user = device.startswith('network:')

        if is_network_user:
            session.su = False
            session.bot = False
            io.network_input_queue = asyncio.Queue()
        else: # Covers console and other device (bot) users
            session.su = is_console_user
            session.bot = not is_console_user
            # network_input_queue is not needed

        self.contexts[user] = io
        return io

    async def run_post_login_setup(self, io: Context):
        """Runs startup scripts and other setup after a user is fully logged in."""
        if not io or not io.session.user:
            return

        # Display MOTD if not joining a room.
        # This mirrors the logic for network clients in port.py.
        if not (self.os.chat and self.os.chat.active_room):
            motd_content = getattr(io, 'motd_cache', None)
            if motd_content:
                await io.print(motd_content)

        # Execute system-wide skrc
        skrc_global_path = self.os.SKRC
        if exists(self.os.fs.box(skrc_global_path)):
            await self.os.proc.exec(io, skrc_global_path)

        # Execute user-specific .skrc
        # The user's PWD is set to their home directory (e.g., /root, /home/user)
        # So we can construct the .skrc path relative to PWD.
        skrc_user_path = posixpath.join(io.pwd, '.skrc')
        if await self.os.fs.exists(io, skrc_user_path): # Use self.exists as it handles virtual paths properly
            await self.os.proc.exec(io, skrc_user_path)

        if self.os.chat and self.os.chat.active_room:
            await self.os.chat.add_to_room(io)

    async def login(self, user, device=None, interactive:bool=True,
                    connect=None, io_callback=None):
        """Log-in to get a Context."""
        await self.os.ready.wait()
        if self.os.halt.is_set(): return

        if not device:
            device = self.os.CONSOLE_DEV

        elif device != self.os.CONSOLE_DEV \
                and not await self.os.fs.exists(self.os.system, device):
            await self.os.system.error(f'!! device not found: {device}')
            return

        if user in self.contexts:
            await self.os.system.error(f'!! already logged in: {user}')
            return

        elif user == 'iosk': # reserved
            await self.os.system.error(f'!! invalid login name: {user}')
            return

        login_msg = f":: user '{user}' logged in on '{self.os.hostname}'"
        await self.os.system.print(login_msg)

        io = self._initialize_user_context(user, device)

        user_addr = f"{user}.{self.os.hostname}"

        # --- Color Initialization ---
        # Part 1: If the new user is interactive, set up THEIR color map.
        # Bots do not need their own color map as they don't "see" colors.
        if not io.session.bot:
            # This user is interactive, set up their color map with user.host keys.
            # 1a. Assign self-color (white)
            io.session.user_colors[user_addr] = util.COLOR_MAP[util.USER_SELF_COLOR_NAME]

            # 1b. Populate this new user's map with all other known users.
            all_other_users = list(self.os.network_users.keys())
            for u, uio in self.contexts.items():
                # self.users already contains the new user, so we must skip them.
                if u != user:
                    all_other_users.append(f"{u}.{self.os.hostname}")

            for other_addr in all_other_users:
                 io.session.user_colors[other_addr] = self._get_next_color(io)

        # Part 2: Add the new user (bot or not) to all existing interactive users' maps.
        # This allows interactive users to see and set colors for bots.
        for other_io in self.contexts.values():
            if other_io.session.user != user and not other_io.session.bot:
                other_io.session.user_colors[user_addr] = self._get_next_color(other_io)

        # --- CWD and Home Directory Initialization ---
        if user == 'root':
            home_dir_virtual = '/root'
            home_dir_host = self.os.fs.box(home_dir_virtual, io_context=io)

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
            home_dir_host = self.os.fs.box(home_dir_virtual, io_context=io)

            if not os.path.exists(home_dir_host):
                try:
                    os.makedirs(home_dir_host)
                    await io.print(f":: created home directory: {home_dir_virtual}")

                    # Copy /etc/skel/skrc to ~/.skrc if it exists
                    skel_skrc_path = self.os.SKEL_SKRC
                    user_skrc_path = posixpath.join(home_dir_virtual, '.skrc')
                    if await self.os.fs.exists(io, skel_skrc_path):
                        await io.print(f":: copying {skel_skrc_path} to {user_skrc_path}")
                        await self.os.fs.copy(io, skel_skrc_path, user_skrc_path)

                except Exception as e:
                    await self.os.system.error(f"!! failed to create home directory {home_dir_virtual}: {e}")
                    # For now, allow login to proceed but log the error.
            io.pwd = home_dir_virtual # Set the current working directory for the user

        # Determine and cache the MOTD for this session to ensure consistency.
        io.motd_cache = await self.os.fs.get_motd(io)

        if io_callback:
            await io_callback(io)

        if connect:
            if self.os.chat: await self.os.chat.send(user, connect, sys=True)
            else: await io.print(connect)

        # MODIFIED: Update local network_users and then broadcast
        self.os.network_users[user_addr] = {'is_bot': io.session.bot, 'paused': io.session.paused}

        # Announce user login to network peers
        if self.os.port:
            await self.os.port.broadcast_color_updates()
            await self.os.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'login',
                'user': user,
                'host': self.os.hostname,
                'is_bot': io.session.bot,
                'paused': io.session.paused
            })
            # Announce user login to the entire mesh system log
            await self.os.port.broadcast_to_peers({
                'type': 'system_broadcast',
                'message': login_msg
            })

        # For local logins, run post-setup immediately.
        await self.run_post_login_setup(io)

        return io

    async def interactive(self, io):
        while not self.os.halt.is_set():
            start = datetime.now()
            try:
                # This outer try handles Ctrl+C when idle at the prompt
                try:
                    # Determine prompt character based on room status
                    if self.os.chat and self.os.chat.active_room:
                        prompt_char = '>>'
                    else:
                        prompt_char = '$'

                    # --- History Proposal Implementation ---
                    # Construct the prompt with the new prompt number and format.
                    prompt_str = f'[{io.session.user} #{io.session.prompt_number} {io.pwd}] {prompt_char} '
                    # --- End Implementation ---

                    while (text := await io.input(prompt=prompt_str)) is None:
                        # non-blocking inputs return None until data
                        delay = (datetime.now() - start).total_seconds()
                        if delay < 0.1:
                            await asyncio.sleep(0.1 - delay)
                        start = datetime.now()

                    is_room_active = self.os.chat and self.os.chat.active_room

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
                                io.session.history.append(original_command_line)

                            # The `call` function handles adding the command and output
                            # to the AI's session_history. We pass it the command to execute
                            # and the original line for accurate logging.
                            await self.os.proc.call(io, command_to_run, original_command_line)
                        else:   # Is a chat message because we are in a room and not a command.
                            if self.os.chat:
                                # The chat system is responsible for creating history entries
                                # and displaying the message for all participants (including the sender).
                                await self.os.chat.send(io.session.user, line)
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
        if io.session.user not in self.contexts:
            await self.os.system.error(f'!! not logged in: {io.session.user}')
            return False

        logout_msg = f":: user '{io.session.user}' logged off from '{self.os.hostname}'"
        await self.os.system.print(logout_msg)

        user_to_logout = io.session.user
        user_addr_to_logout = f"{user_to_logout}.{self.os.hostname}"
        user_is_network_client = io.dev.startswith('network:')
        del self.contexts[user_to_logout]

        # --- Color Cleanup ---
        for remaining_io in self.contexts.values():
            if not remaining_io.session.bot and user_addr_to_logout in remaining_io.session.user_colors:
                del remaining_io.session.user_colors[user_addr_to_logout]

        if disconnect:
            if self.os.chat: await self.os.chat.send(user_to_logout, disconnect, sys=True)
            else: await io.print(disconnect)

        # MODIFIED: Update local network_users and then broadcast
        if user_addr_to_logout in self.os.network_users:
            del self.os.network_users[user_addr_to_logout]

        # Announce user logout to network peers
        if self.os.port:
            await self.os.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'logout',
                'user': user_to_logout,
                'host': self.os.hostname
            })
            # Announce user logout to the entire mesh system log
            await self.os.port.broadcast_to_peers({
                'type': 'system_broadcast',
                'message': logout_msg
            })

            # Update all local clients about the state change
            if self.os.chat:
                await self.os.chat._broadcast_room_state_update()
            await self.os.port.broadcast_color_updates()

            # If the user was a network client, close their connection
            if user_is_network_client:
                await self.os.port.disconnect_client(user_to_logout)
        else:
            # Handle non-networked case (e.g. local bot logout)
            if self.os.chat:
                await self.os.chat._broadcast_room_state_update()

        return True

    async def login_network_user(self, username, websocket):
        """Called by PortManager to log in a user from a network client."""
        await self.os.ready.wait()
        if self.os.halt.is_set(): return None

        if username in self.contexts:
            await self.os.system.error(f"!! login failed: user '{username}' already logged in.")
            return None

        login_msg = f":: user '{username}' logged in on '{self.os.hostname}' (client)"
        await self.os.system.print(login_msg)

        device_path = f"network:{id(websocket)}"
        io = self._initialize_user_context(username, device_path)

        user_addr = f"{username}.{self.os.hostname}"

        # --- Color Initialization (for network user) ---
        # Part 1: If the new user is interactive, set up THEIR color map.
        if not io.session.bot:
            # This user is interactive, set up their color map with user.host keys.
            # 1a. Assign self-color (white)
            io.session.user_colors[user_addr] = util.COLOR_MAP[util.USER_SELF_COLOR_NAME]

            # 1b. Populate this new user's map with all other known users.
            all_other_users = list(self.os.network_users.keys())
            for u, uio in self.contexts.items():
                if u != username:
                    all_other_users.append(f"{u}.{self.os.hostname}")

            for other_addr in all_other_users:
                 io.session.user_colors[other_addr] = self._get_next_color(io)

        # Part 2: Add the new user (bot or not) to all existing interactive users' maps.
        for other_io in self.contexts.values():
            if other_io.session.user != username and not other_io.session.bot:
                other_io.session.user_colors[user_addr] = self._get_next_color(other_io)

        if username == 'root':
            home_dir_virtual = '/root'
            home_dir_host = self.os.fs.box(home_dir_virtual, io_context=io)

            if not os.path.exists(home_dir_host):
                io.pwd = '/'
                await self.os.system.print(f":: Network root login: /root home directory not found. Setting PWD to /")
            else:
                io.pwd = home_dir_virtual
                await self.os.system.print(f":: Network root login: root home directory is {home_dir_virtual}")
        else:
            home_dir_virtual = f'/home/{username}'
            home_dir_host = self.os.fs.box(home_dir_virtual, io_context=io)
            if not os.path.exists(home_dir_host):
                try:
                    os.makedirs(home_dir_host)
                    # For network users, output these messages to the system log, not their non-existent local console.
                    await self.os.system.print(f":: created home directory for network user {username}: {home_dir_virtual}")
                    skel_skrc_path = self.os.SKEL_SKRC
                    user_skrc_path = posixpath.join(home_dir_virtual, '.skrc')
                    if await self.os.fs.exists(io, skel_skrc_path):
                        await self.os.system.print(f":: copying {skel_skrc_path} to {user_skrc_path} for network user {username}")
                        await self.os.fs.copy(io, skel_skrc_path, user_skrc_path)
                except Exception as e:
                    await self.os.system.error(f"!! failed to create home directory {home_dir_virtual} for network user {username}: {e}")
            io.pwd = home_dir_virtual

        # Determine and cache the MOTD for this session to ensure consistency.
        io.motd_cache = await self.os.fs.get_motd(io)

        # MODIFIED: Update local network_users and then broadcast
        self.os.network_users[user_addr] = {'is_bot': io.session.bot, 'paused': io.session.paused}

        if self.os.port:
            await self.os.port.broadcast_color_updates()
            await self.os.port.broadcast_to_peers({
                'type': 'user_update',
                'action': 'login',
                'user': username,
                'host': self.os.hostname,
                'is_bot': io.session.bot,
                'paused': io.session.paused
            })
            await self.os.port.broadcast_to_peers({
                'type': 'system_broadcast',
                'message': login_msg
            })

        # Do not run post-login setup here. The PortManager will do it.
        asyncio.create_task(self.interactive(io))

        return io

    async def logout_network_user(self, username):
        """Called by PortManager when a client disconnects."""
        if username in self.contexts:
            io = self.contexts[username]
            await self.logout(io, disconnect=f':: {username} has disconnected (network)')

    async def handle_client_input(self, username, data):
        """Called by PortManager to feed input to a network user's session."""
        if username in self.contexts:
            io = self.contexts[username]
            if hasattr(io, 'network_input_queue') and isinstance(io.network_input_queue, asyncio.Queue):
                await io.network_input_queue.put(data)
