# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig


MODEL = 'gemini-2.0-flash'
TIMEOUT = 3 * 60 * 1000 # wait up to 3 minutes (file uploads, etc.)


async def iosend(iosk, args):
    #print(f'GEMINI: {args}')
    prompt = args
    api_key = await iosk.get('/etc/gemini')
    api_key = api_key.strip()

    client = genai.Client(api_key=api_key,
                          http_options=HttpOptions(timeout=TIMEOUT))

    resp = await client.aio.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=['TEXT'],
            ),
        )

    return resp.text

