import aioconsole
import asyncio

async def iosend(io, data):
    await aioconsole.aprint(data, end='')


async def iorecv(io, prompt=None):
    await aioconsole.aprint(prompt, end='')
    try:
        return await aioconsole.ainput()

    except Exception as e:
        #print(e)
        pass

