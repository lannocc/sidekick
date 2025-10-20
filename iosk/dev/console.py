import aioconsole
import asyncio

async def iosend(io, data):
    try:
        await aioconsole.aprint(data, end='')
    except:
        if io.os.halt.is_set():
            # We are shutting down and our async console has already terminated.
            # Default back to regular print:
            print(data, end='')
        else:
            raise


async def iorecv(io, prompt=None):
    await aioconsole.aprint(prompt, end='')
    try:
        return await aioconsole.ainput()
    except (EOFError, KeyboardInterrupt):
        raise
    except asyncio.CancelledError:
        # Transform the asyncio-specific cancellation on Ctrl+C into the
        # general KeyboardInterrupt that the kernel's interactive loop expects.
        raise KeyboardInterrupt from None
    except Exception as e:
        pass

