# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig


DEFAULT_MODEL = 'gemini-2.5-flash'
TIMEOUT = 3 * 60 * 1000 # wait up to 3 minutes (file uploads, etc.)

client = None


async def iosend(io, data):
    prompt = data
    io.os.chat.engagements[io.user].append(prompt, trip)
    await online(io)


async def iosender(io, data, model):
    prompt = data
    async def mtrip(prompt):
        return await trip(prompt=prompt, model=model)
    io.os.chat.engagements[io.user].append(prompt, mtrip)
    await online(io)


async def iorecv(io):
    if io.user not in io.os.chat.engagements: return None
    data = await io.os.chat.engagements[io.user].input()
    return data


async def online(io):
    global client

    if not client:
        #print('GETTING GOOGLE CLIENT')
        api_key = await io.os.get(io, '/etc/google')
        api_key = api_key.strip()
        if not api_key:
            await io.parent.error('!! no api key')
            return
        client = genai.Client(api_key=api_key,
                              http_options=HttpOptions(timeout=TIMEOUT))


async def trip(prompt, model=DEFAULT_MODEL): # round trip
    #print(f'SENDING TO GOOGLE: {prompt}')
    resp = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=['TEXT'],
            ),
        )

    reply = resp.text
    #print(f'GOT GOOGLE REPLY: {reply}')

    return reply

