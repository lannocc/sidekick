# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush as print

import asyncio
from datetime import datetime
from os.path import exists


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
            engage = Engagement(dev)
            self.engagements[dev] = engage

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
        if io.dev in self.engagements:
            self.engagements[io.dev].enabled = False
            del self.engagements[io.dev]

        await self.os.logout(io, disconnect=f':: {io.user} has left the chat')

    async def send(self, from_user, msg, sys=False):
        if not msg: return
        if not sys: msg = f'<< [{from_user}] {msg}'

        for user, uio in self.os.users.items():
            if user is from_user: continue
            await uio.print(msg)


class Engagement:
    SECS_SEND_AFTER_IDLE = 2.3
    SECS_POLL_REPLY_AFTER = 27

    PREAMBLE = '/sbin/preamble'
    POSTAMBLE = '/sbin/postamble'

    def __init__(self, dev):
        self.dev = dev
        self.enabled = True

        #self.history = ''
        self.buf = None # FIXME this has been replaced by Context.session ?
        self.last_buf = None
        self.trip = None
        self.inbuf = None

        self.io = None

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
        self.inbuf = None
        return data

    async def ioset(self, io):
        self.io = io

    async def engage(self): # buffer outputs and poll for replies
        last_talk = datetime.now()

        while self.enabled:
            prompt = None

            # is buffered output waiting and ready to send?
            if self.buf and (datetime.now() - self.last_buf).total_seconds() \
                    >= self.SECS_SEND_AFTER_IDLE:
                #print(f'SENDING TO {self.dev}: {self.buf}')

                self.io.session.seek(0)
                prompt = self.io.session.read() #+ self.buf
                self.buf = None
                self.last_buf = None

            # or is there no output but we're ready to check for input?
            elif not self.buf and (datetime.now() - last_talk).total_seconds() \
                    >= self.SECS_POLL_REPLY_AFTER:
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
                       + '\n=================== IOSK CHAT HISTORY BEGIN ===\n' \
                       + prompt \
                       + '\n=================== IOSK CHAT HISTORY   END ===\n' \
                       + post

                finally:
                    self.io.stage_normal()

                #print('++++++++++++++++++++++++++++++++++++++ PROMPT BEGIN +++')
                #print(prompt)
                #print('++++++++++++++++++++++++++++++++++++++ PROMPT   END +++')

                reply = await self.trip(prompt)

                #print('-------------------------------------- REPLY  BEGIN ---')
                #print(reply)
                #print('-------------------------------------- REPLY    END ---')

                if reply:
                    reply += '\n' # they hit the enter key (keeps history good)
                    if self.inbuf: self.inbuf += '\n' + reply
                    else: self.inbuf = reply

                last_talk = datetime.now()

            await asyncio.sleep(0.1)

    def read_history(self):
        pass

