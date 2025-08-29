# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush as print

import asyncio
from datetime import datetime


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
                                 io_callback=engage.start if engage else None)

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

    def __init__(self, dev):
        self.dev = dev
        self.enabled = True

        #self.history = ''
        self.buf = None
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

    async def start(self, io):
        self.io = io

    async def engage(self): # buffer outputs and poll for replies
        last_talk = datetime.now()

        while self.enabled:
            prompt = None

            # is buffered output waiting and ready to send?
            if self.buf and (datetime.now() - self.last_buf).total_seconds() \
                    >= self.SECS_SEND_AFTER_IDLE:
                #print(f'SENDING TO {self.dev}: {self.buf}')

                #prompt = self.buf # buffer starts with full history
                self.io.session.seek(0)
                prompt = self.io.session.read() + self.buf
                self.buf = None
                self.last_buf = None

            # or is there no output but we're ready to check for input?
            elif not self.buf and (datetime.now() - last_talk).total_seconds() \
                    >= self.SECS_POLL_REPLY_AFTER:
                #print('POLLING FOR REPLY')
                #prompt = self.history
                self.io.session.seek(0)
                prompt = self.io.session.read()

            if prompt:
                reply = await self.trip(prompt)
                if reply:
                    reply += '\n' # they hit the enter key (keeps history good)
                    if self.inbuf: self.inbuf += '\n' + reply
                    else: self.inbuf = reply

                last_talk = datetime.now()

            await asyncio.sleep(0.1)

    def read_history(self):
        pass

