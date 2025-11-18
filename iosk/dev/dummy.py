# ./dev/dummy.py
import asyncio
from datetime import datetime, timedelta
import random

class DummyClient:
    """A placeholder client for the dummy device, which has no external service."""
    pass

async def get_client(io):
    """
    Returns a dummy client instance. Required by the kernel's device model.
    """
    return DummyClient()

async def iosend(io, data):
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return None
    # The trip function is passed to the engagement system. It will be called
    # later with the client (from get_client) and the prompt.
    engagement.append(data, trip)

async def iorecv(io, prompt=None):
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return None
    data = await engagement.input()
    return data

async def trip(client, prompt): # round trip
    """
    Performs a simulated round trip.
    The 'client' argument is required by the new kernel architecture but is not used here.
    """
    print(f'***DUMMY SEE: {prompt}')
    reply = 'hello\nblah blah blah\ncool' if random.randint(1, 5) == 1 else None
    if reply: print(f'***DUMMY SAY: {reply}')
    return reply