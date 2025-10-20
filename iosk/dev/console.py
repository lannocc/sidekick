import aioconsole
import asyncio

async def iosend(io, data):
    await aioconsole.aprint(data, end='')


async def iorecv(io, prompt=None):
    await aioconsole.aprint(prompt, end='')
    try:
        return await aioconsole.ainput()
    except EOFError:
        # Re-raise EOFError so the kernel's interactive loop can catch it
        # and gracefully log the user out. This is the fix.
        raise
    except Exception as e:
        # For other unexpected exceptions, we maintain the original behavior
        # of passing to avoid a crash, but the critical EOFError is now handled.
        #print(e)
        pass

