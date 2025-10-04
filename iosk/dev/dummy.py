# ./dev/dummy.py
import asyncio
from datetime import datetime, timedelta
import random

async def iosend(io, data):
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return None
    engagement.append(data, trip)

async def iorecv(io, prompt=None):
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return None
    data = await engagement.input()
    return data

async def trip(prompt): # round trip
    print(f'***DUMMY SEE: {prompt}')
    reply = 'hello\nblah blah blah\ncool' if random.randint(1, 5) == 1 else None
    if reply: print(f'***DUMMY SAY: {reply}')
    return reply

