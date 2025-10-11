from sk.iosk.dev.ollama import iosender, iorecv


async def iosend(io, data):
    await iosender(io, data, 'gpt-oss')

