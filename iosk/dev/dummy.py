# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import asyncio
from datetime import datetime, timedelta
import random


async def iosend(io, data):
    io.os.chat.engagements[io.dev].append(data, trip)


async def iorecv(io):
    if io.dev not in io.os.chat.engagements: return None
    data = io.os.chat.engagements[io.dev].input()
    return data


async def trip(prompt): # round trip
    print(f'***DUMMY SEE: {prompt}')
    reply = 'hello\nblah blah blah\ncool' if random.randint(1, 5) == 1 else None
    if reply: print(f'***DUMMY SAY: {reply}')
    return reply

