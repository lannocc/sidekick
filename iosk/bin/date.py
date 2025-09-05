from datetime import datetime

async def iocall(io, args):
    await io.print(datetime.now().strftime('%A, %b %d, %Y at %I:%M %p'))

