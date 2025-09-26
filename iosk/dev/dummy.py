import asyncio
from datetime import datetime, timedelta
import random

async def iosend(io, data):
    io.os.chat.engagements[io.user].append(data, trip)

async def iorecv(io):
    if io.user not in io.os.chat.engagements: return None
    data = await io.os.chat.engagements[io.user].input()
    return data

async def trip(prompt): # round trip
    print(f'***DUMMY SEE: {prompt}')
    reply = 'hello\nblah blah blah\ncool' if random.randint(1, 5) == 1 else None
    if reply: print(f'***DUMMY SAY: {reply}')
    return reply

