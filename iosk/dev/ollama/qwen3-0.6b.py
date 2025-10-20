from sk.iosk.dev.ollama import iosender, iorecv, get_client


async def iosend(io, data):
    await iosender(io, data, 'qwen3:0.6b')

