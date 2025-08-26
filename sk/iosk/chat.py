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
            self.engagements[dev] = Engagement()

        io = await self.os.login(user=name, device=dev, interactive=False,
                                 connect=connect)

        async def go(io):
            await self.os.interactive(io)
            await self.leave(io)

        if engage:
            asyncio.create_task(go(io))
            asyncio.create_task(self.engage(dev))

        #print(f'RETURN FROM JOIN: {name}')
        return io

    async def leave(self, io):
        if io.user in self.engagements:
            del self.engagements[io.user]

        await self.os.logout(io, disconnect=f':: {io.user} has left the chat')

    async def send(self, from_user, msg, sys=False):
        if not msg: return
        if not sys: msg = f'<< [{from_user}] {msg}'

        for user, uio in self.os.users.items():
            if user is from_user: continue
            await uio.print(msg)

    async def engage(self, dev): # buffer outputs
        last = None

        while dev in self.engagements:
            eng = self.engagements[dev]

            if eng.buf and (datetime.now() - eng.now).total_seconds() >= 1:
                #print(f'SENDING TO {dev}: {eng.buf}')

                prompt = eng.buf
                eng.buf = None
                eng.now = None

                reply = await eng.trip(prompt)
                if eng.inbuf: eng.inbuf += '\n' + reply
                else: eng.inbuf = reply
                last = datetime.now()

            elif not eng.buf and (datetime.now() - last).total_seconds() >= 5:
                #print('POLLING FOR REPLY')
                reply = await eng.trip(eng.history)
                if eng.inbuf: eng.inbuf += '\n' + reply
                else: eng.inbuf = reply
                last = datetime.now()

            await asyncio.sleep(0.1)


class Engagement:
    def __init__(self):
        self.history = ''
        self.buf = None
        self.now = None
        self.trip = None
        self.inbuf = None

    def append(self, text, trip):
        self.trip = trip
        self.now = datetime.now()

        self.history += text
        if self.buf: self.buf += text
        else: self.buf = self.history

    def input(self):
        data = self.inbuf
        if data is not None:
            self.history += data
        self.inbuf = None
        return data

