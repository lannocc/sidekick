# src/iosk/chat.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import print_flush as print

import tiktoken
#from google.api_core.exceptions import ResourceExhausted
from google.genai.errors import ClientError

import asyncio
from datetime import datetime
from os.path import exists, join
import re
import tempfile
import traceback
import uuid


class AIMessenger:
    def __init__(self, iosk):
        iosk.chat = self
        self.os = iosk
        self.engagements = { }

        # Netroom state attributes
        self.active_room = None
        self.room_topic = None
        self.room_owner = None
        self.local_room_participants = set()

    async def _setup_chat_context(self, io):
        """Executes preamble, caches it, and calculates initial token counts."""
        # --- Preamble Caching ---
        io.stage_pre()
        try:
            preamble_path = '/etc/chat/preamble'
            if await self.os.exists(io, preamble_path):
                await self.os.exec(io, preamble_path)
            if io.pre:
                io.pre.seek(0)
                io.preamble_cache = io.pre.read()
            else:
                io.preamble_cache = ""
        finally:
            io.stage_normal()

        # --- Token Calculation for Initial Static Context ---
        try:
            encoding = tiktoken.get_encoding('cl100k_base')

            # Preamble part
            static_content = io.preamble_cache or ""

            # Banking part
            banking = ''
            if io.banks:
                for bank_acct, data in io.banks.items():
                    banking += '\n' + data + '\n'

            if banking:
                static_content += ('\n=== CORE RULES/MEMORY BEGIN ===\n'
                                   'THIS SECTION IS MOST IMPORTANT, I MUST ALWAYS REMEMBER:\n'
                                   f'{banking}'
                                   '\n=== END   CORE RULES/MEMORY ===\n')

            initial_static_tokens = len(encoding.encode(static_content))
            io.caching_token_total = initial_static_tokens # Initialize the running total
            io.initial_static_tokens = initial_static_tokens
        except Exception as e:
            # AIs might not be used, so don't fail login if tiktoken is missing
            # or something goes wrong. Just log it.
            await self.os.system.error(f"!! token initialization failed: {e}")

    async def join(self, name, dev=None): # no device means local (self)
        assert name
        connect = f':: {name} has entered the chat from {dev or "local"}'
        engage = True if dev else False
        if not dev: dev = self.os.CONSOLE_DEV

        if engage:
            engage = Engagement(name)
            self.engagements[name] = engage

        io = await self.os.login(user=name, device=dev, interactive=False,
                                 connect=connect,
                                 io_callback=engage.ioset if engage else None)

        if not io:
            return

        await self._setup_chat_context(io)

        async def go(io):
            await self.os.interactive(io)
            await self.leave(io)

        if engage:
            asyncio.create_task(go(io))
            asyncio.create_task(engage.engage())

        #print(f'RETURN FROM JOIN: {name}')
        return io

    async def leave(self, io):
        await self.remove_from_room(io.user)

        if io.user in self.engagements:
            self.engagements[io.user].enabled = False
            del self.engagements[io.user]

        msg = f':: {io.user} has left the chat'
        return await self.os.logout(io, disconnect=msg)

    async def send(self, from_user, msg, sys=False):
        if not msg: return

        # --- System Message Handling (Broadcast to all local users) ---
        if sys:
            for user, uio in self.os.users.items():
                if uio.paused: continue
                await uio.print(msg)
            return

        # --- Direct Message Handling ---
        if msg.startswith('@'):
            parts = msg.split(' ')
            recipients = []
            msg_start_index = 0
            for i, part in enumerate(parts):
                if part.startswith('@') and len(part) > 1:
                    recipients.append(part[1:])
                    msg_start_index = i + 1
                else:
                    break # End of recipient list

            actual_msg = ' '.join(parts[msg_start_index:]).strip()
            if not (recipients and actual_msg):
                 # Not a valid DM, treat as a regular message
                 pass
            else:
                # We have a valid DM
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                remote_from_addr = f"{from_user}.{self.os.hostname}"

                remote_recipients = {} # host -> [user1, user2]
                local_recipients = []

                for r_addr in recipients:
                    if '.' in r_addr:
                        r_user, r_host = r_addr.split('.', 1)
                        if r_host not in remote_recipients:
                            remote_recipients[r_host] = []
                        remote_recipients[r_host].append(r_user)
                    else:
                        local_recipients.append(r_addr)

                # Send to remote users via PortManager
                for host, users in remote_recipients.items():
                    payload = {
                        "type": "direct_message",
                        "from_addr": remote_from_addr,
                        "to_users": users,
                        "content": actual_msg
                    }
                    await self.os.port.route_message(host, payload)

                # Send to local users
                for user in local_recipients:
                    if user == from_user: continue
                    if user in self.os.users:
                        uio = self.os.users[user]
                        if not uio.paused:
                            # For local recipients, the sender is local, so don't show host.
                            # ADDED: ASCII BELL character '\a' for terminal ring
                            dm_msg = f'\a\n[{from_user} -> me {now}] << {actual_msg}'
                            await uio.print(dm_msg)

                # Send confirmation to sender
                sender_io = self.os.users.get(from_user)
                if sender_io:
                    recipient_str = ', '.join(recipients)
                    dm_conf = f'\n[me -> {recipient_str} {now}] << {actual_msg}'
                    await sender_io.print(dm_conf)

                return # End of DM handling

        # --- Room Broadcast Handling ---
        if self.active_room:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            remote_from_addr = f"{from_user}.{self.os.hostname}"

            # Broadcast to local participants
            # For local participants, the sender is also local, so don't show host.
            local_msg = f'\n[{from_user} {now}] << {msg}'
            for user in self.local_room_participants:
                if user in self.os.users:
                    await self.os.users[user].print(local_msg)

            # Broadcast to network peers
            payload = {
                "type": "room_message",
                "msg_id": str(uuid.uuid4()),
                "from_addr": remote_from_addr,
                "room_name": self.active_room,
                "content": msg
            }
            await self.os.port.broadcast_to_peers(payload)
        else:
            # No active room, inform the user
            sender_io = self.os.users.get(from_user)
            if sender_io:
                await sender_io.error("!! No active room. Use 'room <name>' to start one.")

    # --- Netroom Lifecycle API ---

    async def open_room(self, io, room_name: str) -> bool:
        if self.active_room:
            await io.error(f"!! A room ('{self.active_room}') is already active on this system.")
            return False

        self.active_room = room_name
        self.room_owner = io.user
        self.local_room_participants = set(self.os.users.keys())

        # Update the kernel's network_rooms state for local users
        for user in self.local_room_participants:
            user_addr = f"{user}.{self.os.hostname}"
            self.os.network_rooms[user_addr] = room_name

        room_dir = join('/var/room', room_name)
        owner_file = join(room_dir, 'owner')
        topic_file = join(room_dir, 'topic')
        motd_file = join(room_dir, 'motd')

        if not await self.os.exists(io, room_dir):
            await self.os.create_dir(io, room_dir, parents=True)
            await self.os.create(io, owner_file)
            # This is a bit awkward. create+write would be better.
            with open(self.os.box(owner_file), 'w') as f:
                f.write(io.user)

        self.room_topic = await self.os.get(io, topic_file)
        motd = await self.os.get(io, motd_file)

        # Announce room opening to system logs and mesh
        open_msg = f":: room '{room_name}' opened on '{self.os.hostname}' by '{io.user}'"
        await self.os.system.print(open_msg)

        await io.print(f":: room '{room_name}' opened.")
        if motd:
            await io.print(motd)

        await self.os.port.broadcast_to_peers({
            'type': 'room_update',
            'action': 'open',
            'name': self.active_room,
            'host': self.os.hostname,
            'owner': self.room_owner,
            'topic': self.room_topic
        })
        # Broadcast system message to all hosts
        await self.os.port.broadcast_to_peers({'type': 'system_broadcast', 'message': open_msg})
        return True

    async def close_room(self, io) -> bool:
        if not self.active_room:
            await io.error("!! No room is currently active.")
            return False

        if not io.su and io.user != self.room_owner:
            await io.error(f"!! Permission denied. Only the owner ('{self.room_owner}') or a superuser can close the room.")
            return False

        closing_msg = f":: room '{self.active_room}' is closing."
        await self.send(self.os.hostname, closing_msg, sys=True)

        closed_room_name = self.active_room

        # Announce room closing to system logs and mesh
        close_msg = f":: room '{closed_room_name}' closed on '{self.os.hostname}' by '{io.user}'"
        await self.os.system.print(close_msg)

        # Update the kernel's network_rooms state for local users
        users_in_closed_room = list(self.local_room_participants) # copy before clearing
        for user in users_in_closed_room:
            user_addr = f"{user}.{self.os.hostname}"
            if user_addr in self.os.network_rooms:
                del self.os.network_rooms[user_addr]

        self.active_room = None
        self.room_topic = None
        self.room_owner = None
        self.local_room_participants.clear()

        await io.print(f":: room '{closed_room_name}' closed.")

        await self.os.port.broadcast_to_peers({
            'type': 'room_update', 'action': 'close', 'name': closed_room_name, 'host': self.os.hostname
        })
        # Broadcast system message to all hosts
        await self.os.port.broadcast_to_peers({'type': 'system_broadcast', 'message': close_msg})
        return True

    async def add_to_room(self, target_io) -> bool:
        if not self.active_room:
            await target_io.error("!! Cannot join: no room is active.")
            return False

        self.local_room_participants.add(target_io.user)

        # Update network_rooms for the new user
        user_addr = f"{target_io.user}.{self.os.hostname}"
        self.os.network_rooms[user_addr] = self.active_room

        motd_file = join('/var/room', self.active_room, 'motd')
        motd = await self.os.get(target_io, motd_file)
        if motd:
            await target_io.print(motd)

        arrival_msg = f":: {target_io.user} has joined the room."
        for user in self.local_room_participants:
            if user != target_io.user and user in self.os.users:
                await self.os.users[user].print(arrival_msg)

        return True

    async def remove_from_room(self, user_name: str):
        if user_name in self.local_room_participants:
            self.local_room_participants.remove(user_name)

            # Update network_rooms for the departing user
            user_addr = f"{user_name}.{self.os.hostname}"
            if user_addr in self.os.network_rooms:
                del self.os.network_rooms[user_addr]

            # Announce departure
            departure_msg = f":: {user_name} has left the room."
            for user in self.local_room_participants:
                await self.os.users[user].print(departure_msg)

    async def handle_network_message(self, message: dict):
        msg_type = message.get("type")

        if msg_type == "room_message":
            if self.active_room and message.get("room_name") == self.active_room:
                from_addr = message.get("from_addr", "unknown.unknown")
                content = message.get("content", "")
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                display_addr = from_addr
                if '.' in from_addr:
                    r_user, r_host = from_addr.split('.', 1)
                    if r_host == self.os.hostname:
                        display_addr = r_user

                local_msg = f'\n[{display_addr} {now}] << {content}'

                for user in self.local_room_participants:
                    if user in self.os.users:
                        await self.os.users[user].print(local_msg)

        elif msg_type == "direct_message":
            to_users = message.get("to_users", [])
            from_addr = message.get("from_addr", "unknown.unknown")
            content = message.get("content", "")
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            display_addr = from_addr
            if '.' in from_addr:
                r_user, r_host = from_addr.split('.', 1)
                if r_host == self.os.hostname:
                    display_addr = r_user

            for user in to_users:
                if user in self.os.users:
                    uio = self.os.users[user]
                    # ADDED: ASCII BELL character '\a' for terminal ring
                    dm_msg = f'\a\n[{display_addr} -> me {now}] << {content}'
                    await uio.print(dm_msg)

class Engagement:
    CODE = 0 # per-run code instance counter

    SECS_IDLE_BEFORE_TRIP = 2.3
    SECS_NOISY_WAIT_REPLY = 13
    SECS_QUIET_IDLE_POLL = 22

    PREAMBLE = '/etc/chat/preamble'
    POSTAMBLE = '/etc/chat/postamble'

    # not greedy:
    #CODEBLOCK_REGEX = re.compile(r'```(?P<language>\w*?)\n(?P<code>.*?)\n```',
    #                             re.DOTALL)

    # greedy (to last ```):
    CODEBLOCK_REGEX = re.compile(r'```(?P<language>\w*?)\n(?P<code>.*)\n```',
                                 re.DOTALL)

    def __init__(self, user):
        self.user = user
        self.enabled = True

        #self.history = ''
        self.buf = None # FIXME this has been replaced by Context.session ?
        self.last_buf = None
        self.trip = None
        self.inbuf = None

        self.io = None
        self.waiting = False # True if currently waiting for reply

    def append(self, text, trip):
        self.trip = trip
        self.last_buf = datetime.now()

        #self.history += text
        if self.buf: self.buf += text
        #else: self.buf = self.history
        else: self.buf = text

    async def input(self):
        data = self.inbuf
        #if data is not None: self.history += data
        if data: data = await self._handle_code_blocks_(data)
        self.inbuf = None
        return data

    async def ioset(self, io):
        self.io = io

    async def engage(self): # buffer outputs and poll for replies
        last_trip = datetime.now()

        while self.enabled:
            if self.io and self.io.paused:
                await asyncio.sleep(1.0) # Check every second if still paused
                continue

            await asyncio.sleep(0.42)

            if self.waiting:
                continue

            prompt = None
            now = datetime.now()
            secs_since_buf = (now - self.last_buf).total_seconds() \
                    if self.last_buf else None
            secs_since_trip = (now - last_trip).total_seconds()

            # is buffered output waiting?
            if self.buf:
                # and it's time to respond?
                if secs_since_buf >= self.SECS_IDLE_BEFORE_TRIP \
                        or secs_since_trip >= self.SECS_NOISY_WAIT_REPLY:
                    #print(f'SENDING TO {self.dev}: {self.buf}')

                    self.io.session.seek(0)
                    prompt = self.io.session.read() #+ self.buf
                    self.buf = None
                    self.last_buf = None

            # or is there no output but we're ready to check for input?
            elif secs_since_trip >= self.SECS_QUIET_IDLE_POLL:
                #print('POLLING FOR REPLY')
                self.io.session.seek(0)
                prompt = self.io.session.read()

            # FIXME: note we didn't actually use the buffer directly...
            #       just an indicator above that there was data waiting
            #       (Context already has the data in its session buffer)

            if prompt:
                # Retrieve cached preamble
                pre = self.io.preamble_cache or ""

                # solid banking
                banking = ''
                if self.io.banks:
                    for bank_acct, data in self.io.banks.items():
                        banking += '\n' + data + '\n'

                # Execute postamble
                post = ''
                try:
                    self.io.stage_post()
                    post_path = self.io.os.box(self.POSTAMBLE)
                    if exists(post_path):
                        await self.io.os.exec(self.io, self.POSTAMBLE)
                    if self.io.post:
                        self.io.post.seek(0)
                        post = self.io.post.read()
                finally:
                    self.io.stage_normal()


                if banking:
                    banking = '' \
                        + '\n=== CORE RULES/MEMORY BEGIN ===\n' \
                        + 'THIS SECTION IS MOST IMPORTANT, I MUST ALWAYS ' \
                        + 'REMEMBER:\n' \
                        + banking \
                        + '\n=== END   CORE RULES/MEMORY ===\n'

                # Determine the correct prompt character for the AI's context
                # This mirrors the logic in kernel.interactive
                if self.io.os.chat and self.io.os.chat.active_room:
                    prompt_char = '>>'
                else:
                    prompt_char = '$'

                prompt_text_for_trip = pre + banking \
                   + '\n=== IOSK PERSONAL CHAT HISTORY BEGIN ===\n' \
                   + prompt \
                   + '\n=== END   IOSK PERSONAL CHAT HISTORY ===\n' \
                   + '\n' + post \
                   + f'\n[{self.io.user} {self.io.pwd}] {prompt_char} '

                # --- Update Running Token Totals ---
                try:
                    encoding = tiktoken.get_encoding('cl100k_base')

                    # Calculate tokens for the dynamic part of the prompt
                    # The 'prompt' var here is just the chat history.
                    dynamic_content = ('\n=== IOSK PERSONAL CHAT HISTORY BEGIN ===\n'
                                       f'{prompt}'
                                       '\n=== END   IOSK PERSONAL CHAT HISTORY ===\n\n'
                                       f'{post}')
                    dynamic_tokens = len(encoding.encode(dynamic_content))

                    # Full prompt tokens for this trip
                    full_prompt_tokens = self.io.initial_static_tokens + dynamic_tokens

                    # Update running totals
                    self.io.caching_token_total += dynamic_tokens
                    self.io.full_token_total += full_prompt_tokens

                except Exception as e:
                    # Don't crash the engagement if token calculation fails
                    await self.io.os.system.error(f"!! token calculation failed during trip: {e}")

                self.waiting = True
                reply = None

                # --- Token Rate Limiting: Proactive Check ---
                try:
                    encoding = tiktoken.get_encoding('cl100k_base')
                    prompt_tokens = len(encoding.encode(prompt_text_for_trip))
                except Exception:
                    prompt_tokens = len(prompt_text_for_trip) // 4 # Fallback estimate

                # Await readiness (waits for cooldowns and throttles if TPM is high)
                await self.io.os.await_device_readiness(self.io.user, self.io.dev, prompt_tokens)

                client = await self.io.os.get_device_client(self.io, self.io.dev)

                if not client:
                    await asyncio.sleep(5.0)
                    self.waiting = False
                else:
                    for attempt in range(3): # Retry loop
                        try:
                            reply = await self.trip(client, prompt_text_for_trip)
                            # Success, break the retry loop
                            break
                        except ClientError as e:
                            if "429" in str(e):
                                # This is a rate limit error, handle it reactively
                                await self.io.os.system.error(f':: API rate limit hit for {self.io.user} on {self.io.dev}: {e}')
                                await self.io.print(":: API rate limit hit. Analyzing cooldown...")

                                # Parse delay from error message, with a fallback
                                match = re.search(r"'retryDelay': '(\d+)s'", str(e))
                                delay = int(match.group(1)) + 2 if match else 15

                                await self.io.os.system.print(f":: Enforcing device cooldown for {delay} seconds.")
                                await self.io.print(f":: Enforcing device cooldown for {delay} seconds.")

                                # Trigger kernel to manage cooldown (runs in background)
                                asyncio.create_task(self.io.os.enforce_cooldown(self.io.dev, delay))

                                # Wait for the cooldown to complete before retrying.
                                await self.io.os.await_device_readiness(self.io.user, self.io.dev, 0)

                                # Continue to the next attempt in the retry loop
                                continue
                            else:
                                # Some other unrecoverable ClientError, fail fast
                                await self.io.os.system.error(f'!! Unhandled Google ClientError for {self.io.user}: {e}')
                                reply = None # ensure reply is None
                                break # exit retry loop
                        except Exception as e:
                            await self.io.os.system.error(f'!! trip (attempt {attempt+1}) for {self.io.user}: {e}')
                            traceback.print_exc()
                            reply = None # ensure reply is None
                            if attempt < 2: # if not the last attempt
                                await asyncio.sleep((attempt + 1) * 1.5) # simple backoff
                            # Let the loop continue to the next attempt

                    # After the loop finishes (either by success, failure, or exhaustion of retries)
                    self.waiting = False
                    await self.io.os.log_trip_trace(self.io, prompt_text_for_trip, reply or "")

                #print('-------------------------------------- REPLY  BEGIN ---')
                #print(reply)
                #print('-------------------------------------- REPLY    END ---')

                if reply:
                    reply += '\n' # they hit the enter key (keeps history good)
                    if self.inbuf: self.inbuf += '\n' + reply
                    else: self.inbuf = reply

                last_trip = datetime.now()

    def _extract_target_from_diff(self, diff_content):
        """Extracts the target filename from a diff's '---' line."""
        # Pattern to find '--- a/path/to/file' or '--- path/to/file'
        match = re.search(r'^--- (?:a/)?([^\t\n]+)', diff_content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None

    async def _handle_code_blocks_(self, text):
        match = next(self.CODEBLOCK_REGEX.finditer(text), None)
        if not match:
            return text

        lang = match.group('language')
        code = match.group('code')
        original_block = match.group(0)

        self.CODE += 1
        # Determine file extension and virtual path
        ext = f'.{lang}' if lang else ''
        if lang == 'diff':
            ext = '.diff'

        filename_stem = f'{self.io.user}-{self.io.os.BOOT}-{self.io.cid}-{self.CODE}'
        filename = f'{filename_stem}{ext}'
        virtual_path = join(self.io.CODE, filename)
        host_path = self.io.os.box(virtual_path)

        # Save the code block to the host file system
        with open(host_path, 'w') as file:
            file.write(code)
            file.write('\n')

        # Special handling for 'diff' blocks
        if lang == 'diff':
            target_file = self._extract_target_from_diff(code)
            if target_file:
                # Print a notification to the local user's context, like command output.
                replacement_message = f':: diff block detected. Attempting to auto-patch `{target_file}`...'
                await self.io.print(replacement_message)

                # Construct and run the patch command. Its output will go directly to the user's console.
                patch_command = f"patch {target_file} {virtual_path}"
                await self.io.os.call(self.io, patch_command)
            else:
                # Could not find a target file, fall back to just saving and notifying locally.
                replacement_message = f':: auto-saved diff block to {virtual_path} (could not determine target file to patch)'
                await self.io.print(replacement_message)

            # Remove the original markdown block from the text that will be processed for chat broadcast.
            return text.replace(original_block, '')

        # Fallback for non-diff code blocks
        # Print the "auto-saved" message directly to the local user's context.
        #replacement_message = f':: iosk auto-saved this markdown block (content hidden) to {virtual_path}'
        replacement_message = f':: iosk auto-saved this markdown block to {virtual_path}'
        await self.io.print(original_block)
        await self.io.print(replacement_message)

        # Remove the original markdown block from the text that will be processed for chat broadcast.
        return text.replace(original_block, '')

