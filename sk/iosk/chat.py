# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from ..util import print_flush as print

import asyncio


class AI_Messenger:
    def __init__(self, iosk):
        iosk.chat = self
        self.iosk = iosk
        self.users = { }

    async def run(self, handle=None):
        async with self.iosk.ready:
            await self.iosk.ready.wait()
            if not self.iosk.started:
                return

        print()
        print('Welcome to the IOSK AI Messenger.')

        if not handle: handle = 'super'
        print(f'You are the super-user: {handle}')

        self.join(handle)
        try:
            while (msg := await self.input(handle, '>> ')) != '$ exit':
                #print(f'<< {msg}')
                if not msg: continue

                if msg.startswith('#'): # comment
                    continue

                elif msg.startswith('$ '): # command
                    await self.iosk.call(msg[2:])

                else: # chat
                    await self.chat(msg)

        except EOFError:
            pass

        finally:
            self.leave(handle)

    def join(self, name, dev=None): # no device means local (self)
        assert name
        #assert name not in self.users

        num = 0
        while name in self.users:
            num += 1
            name = f'{name}{num}'

        self.users[name] = dev or self
        print(f':: {name} has entered the chat from {dev or "local"}')

    def leave(self, name):
        assert name
        #assert name in self.users

        if name not in self.users:
            print(f'!! {name} is not connected')
            return

        del self.users[name]
        print(f':: {name} has left the chat')

    async def input(self, user, prompt=None):
        assert user
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: input(prompt).rstrip())

    async def chat(self, msg):
        if not msg: return
        to=None

        if msg.startswith('@'):
            try: split = msg.index(' ')
            except ValueError: split = len(msg)
            to = msg[1:split]
            msg = msg[split+1:]

        await self.send(msg, to=to)

    async def send(self, msg, to=None):
        #print(f'...sending to {to or "ALL"}...')

        if to:
            if to not in self.users:
                print(f'!! {to} is not online')
                return

            dev = self.users[to]
            if not dev or dev is self: # local loopback
                print(f'<< @{to} {msg}') # echo

            else:
                reply = await self.iosk.send(dev, msg)
                if reply: print(f'<< @{to} {reply}')

        else: # send to everyone
            for handle, dev in self.users.items():
                if not dev or dev is self: # local loopback
                    continue # ignore

                reply = await self.iosk.send(dev, msg)
                if reply: print(f'<< @{handle} {reply}')

