import aioconsole

async def iosend(io, data):
    #print(data)
    await aioconsole.aprint(data, end='')


async def iorecv(io, prompt=None):
    await aioconsole.aprint(prompt, end='')
    return await aioconsole.ainput()

