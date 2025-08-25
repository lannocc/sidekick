# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush as print

import asyncio


class AIMessenger:
    def __init__(self, iosk):
        iosk.chat = self
        self.os = iosk
        self.me = None

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
        io = await self.os.login(user=name, interactive=False, connect=connect)
        return io

    async def leave(self, io):
        await self.os.logout(io, disconnect=f':: {io.user} has left the chat')

    '''
    async def input(self, user, prompt=None):
        assert user
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: input(prompt).rstrip())

    async def chat(self, msg, cmd=None, echo=True, handle=None):
        if not msg: return

        ps = '' if cmd else '<<'
        if handle: handle = f'[@{handle}] '
        else: handle = ''
        if echo: print(f'{ps} {handle}{msg}')

        to=None

        if msg.startswith('@'):
            try: split = msg.index(' ')
            except ValueError: split = len(msg)
            to = msg[1:split]
            msg = msg[split+1:]

        await self.send(msg, to=to, cmd=cmd)

    async def send(self, msg, to=None, cmd=None):
        #print(f'...sending to {to or "ALL"}...')
        #print(f'SEND to={to} cmd={cmd}')

        if to:
            if to not in self.users:
                print(f'!! {to} is not online')
                return

            dev = self.users[to]
            if not dev or dev is self: # local loopback
                print(f'<< @[{to}] {msg}') # echo

            else:
                reply = await self.iosk.send(dev, msg)
                if reply:
                    #print(f'<< @{to} {reply}')
                    await self.chat(reply, cmd=cmd, handle=to)

        else: # send to everyone
            for handle, dev in self.users.items():
                if not dev or dev is self: # local loopback
                    continue # ignore

                reply = await self.iosk.send(dev, msg)
                if reply: print(f'<< @{handle} {reply}')
    '''

