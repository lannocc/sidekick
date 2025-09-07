from sk.iosk.dev.openai import iosender, iorecv


async def iosend(io, data):
    await iosender(io, data, 'gpt-4-turbo')

