# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig

import asyncio
from datetime import datetime, timedelta


MODEL = 'gemini-2.0-flash'
TIMEOUT = 3 * 60 * 1000 # wait up to 3 minutes (file uploads, etc.)

client = None


async def iosend(io, data):
    global client
    #print(f'GEMINI: {data}')
    prompt = data

    io.os.chat.engagements[io.dev].append(prompt, trip)

    if not client:
        #print('GETTING GEMINI CLIENT')
        api_key = await io.os.get(io, '/etc/gemini')
        api_key = api_key.strip()
        if not api_key:
            await io.parent.error('!! no api key')
            return
        client = genai.Client(api_key=api_key,
                              http_options=HttpOptions(timeout=TIMEOUT))


async def iorecv(io):
    if io.dev not in io.os.chat.engagements: return None
    data = io.os.chat.engagements[io.dev].input()
    return data


async def trip(prompt): # round trip
    print(f'SENDING TO GEMINI: {prompt}')
    resp = await client.aio.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=['TEXT'],
            ),
        )

    reply = resp.text
    print(f'GOT GEMINI REPLY: {reply}')

    return reply

