# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush as print

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

        self.engagements = { }

    async def start(self, handle=None):
        print()
        print('Welcome to the IOSK AI Messenger.')

        if not handle: handle = 'root'
        print(f'You are the super-user: {handle}')
        self.me = handle
        return handle

    async def run(self):
        await self.os.ready.wait()
        if self.os.halt.is_set(): return

        io = await self.join(self.me)

        try:
            await self.os.interactive(io)

        finally:
            await self.leave(io)
            #self.me = None

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

        await self.os.logout(io, disconnect=f':: {io.user} has left the chat')

    async def send(self, from_user, msg, sys=False):
        if not msg: return
        if not sys: msg = f'<< [{from_user}] {msg}'

        for user, uio in self.os.users.items():
            if user is from_user: continue
            await uio.print(msg)


class Engagement:
    CODE = 0 # per-run code instance counter

    SECS_IDLE_BEFORE_TRIP = 2.3
    SECS_NOISY_WAIT_REPLY = 13
    SECS_QUIET_IDLE_POLL = 22

    PREAMBLE = '/sbin/preamble'
    POSTAMBLE = '/sbin/postamble'

    CODEBLOCK_REGEX = re.compile(r'```(?P<language>\w+)\n(?P<code>.*?)\n```',
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

    def input(self):
        data = self.inbuf
        #if data is not None: self.history += data
        if data: data = self._handle_code_blocks_(data)
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
                try:
                    # so hacky...
                    self.io.stage_pre()
                    pre = self.io.os.box(self.PREAMBLE)
                    if exists(pre):
                        await self.io.os.exec(self.io, self.PREAMBLE)
                    if self.io.pre:
                        self.io.pre.seek(0)
                        pre = self.io.pre.read()
                    else: pre = ''

                    # solid banking
                    banking = ''
                    if self.io.banks:
                        for bank_acct, data in self.io.banks.items():
                            #banking += '\n~~~' + bank_acct.upper() + '::\n'
                            banking += '\n' + data + '\n'

                    # so hacky...
                    self.io.stage_post()
                    post = self.io.os.box(self.POSTAMBLE)
                    if exists(post):
                        await self.io.os.exec(self.io, self.POSTAMBLE)
                    if self.io.post:
                        self.io.post.seek(0)
                        post = self.io.post.read()
                    else: post = ''

                    prompt = pre \
                       + '\n=== CORE RULES/MEMORY BEGIN ===\n' \
                       + '\nTHIS SECTION IS MOST IMPORTANT, ALWAYS REMEMBER:\n'\
                       + banking \
                       + '\n=== END   CORE RULES/MEMORY ===\n' \
                       + '\n=== IOSK PERSONAL CHAT HISTORY BEGIN ===\n' \
                       + prompt \
                       + '\n=== END   IOSK PERSONAL CHAT HISTORY ===\n' \
                       + post

                finally:
                    self.io.stage_normal()

                #print('++++++++++++++++++++++++++++++++++++++ PROMPT BEGIN +++')
                #print(prompt)
                #print('++++++++++++++++++++++++++++++++++++++ PROMPT   END +++')

                self.waiting = True
                try:
                    reply = await self.trip(prompt)

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

    def read_history(self):
        pass

    def _handle_code_blocks_(self, text):
        matches = self.CODEBLOCK_REGEX.finditer(text)
        replacements = { }

        for match in matches:
            print('YEAHHHHHHHHHHHHHHHHHHHHHHHHHH')
            lang = match.group('language')
            code = match.group('code')

            #fd, temp_file_name = tempfile.mkstemp(prefix=f'iosk_codeblock_',
            #                                      suffix=f'.{lang}')
            #with open(temp_file_name, 'w') as temp_file:
            #    temp_file.write(code)
            #replacements[match.group(0)] = temp_file_name

            self.CODE += 1
            name = f'{self.io.user}-{self.io.os.BOOT}-{self.CODE}.{lang}'
            name = join(self.io.CODE, name)
            path = self.io.os.box(name)

            with open(path, 'w') as file:
                file.write(code)

            replacements[match.group(0)] = name

        for old, new in replacements.items():
            text = text.replace(old, f'IOSK SAVED {new}')

        return text

