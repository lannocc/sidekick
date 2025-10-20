from sk.iosk.dev.openai import iosender, iorecv, get_client


async def iosend(io, data):
    await iosender(io, data, 'gpt-5')

