# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .io import print_flush as print

import tiktoken

import asyncio
from datetime import datetime
from os.path import exists, join
import re
import tempfile


class AIMessenger:
    def __init__(self, iosk):
        iosk.chat = self
        self.os = iosk
        self.me = None
        self.device = None

        self.engagements = { }

    async def start(self, handle=None, device=None):
        print()
        print('Welcome to the IOSK AI Messenger.')

        if not handle: handle = 'root'
        print(f'You are the super-user: {handle}')
        self.me = handle
        self.device = device
        return handle

    async def run(self):
        await self.os.ready.wait()
        if self.os.halt.is_set(): return

        io = await self.join(self.me, dev=self.device)

        try:
            await self.os.interactive(io)

        finally:
            await self.leave(io)
            #self.me = None

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
        if io.user in self.engagements:
            self.engagements[io.user].enabled = False
            del self.engagements[io.user]

        msg = f':: {io.user} has left the chat'
        return await self.os.logout(io, disconnect=msg)

    async def send(self, from_user, msg, sys=False):
        if not msg: return
        if not sys:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            msg = f'\n[{from_user} {now}] << {msg}'

        for user, uio in self.os.users.items():
            if user is from_user: continue
            await uio.print(msg)


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

                prompt_text_for_trip = pre + banking \
                   + '\n=== IOSK PERSONAL CHAT HISTORY BEGIN ===\n' \
                   + prompt \
                   + '\n=== END   IOSK PERSONAL CHAT HISTORY ===\n' \
                   + '\n' + post \
                   + f'\n[{self.io.user} {self.io.pwd}] >> '

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
                try:
                    reply = await self.trip(prompt_text_for_trip)

                except Exception as e: # overloaded?
                    await self.io.os.system.error(f'!! trip for {self.io.user}:'
                                                  f' {e}')
                    await asyncio.sleep(1.8)
                    try:
                        reply = await self.trip(prompt_text_for_trip)

                    except Exception as e: # still overloaded?
                        await self.io.os.system.error(
                                f'!! trip (2) for {self.io.user}: {e}')
                        await asyncio.sleep(4.2)
                        reply = await self.trip(prompt_text_for_trip)

                finally:
                    self.waiting = False

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

