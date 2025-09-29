from sk.iosk.dev.google import iosender, iorecv


async def iosend(io, data):
    await iosender(io, data, 'gemini-2.5-pro')

