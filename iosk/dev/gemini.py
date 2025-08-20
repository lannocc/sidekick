# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig


MODEL = 'gemini-2.0-flash'
TIMEOUT = 3 * 60 * 1000 # wait up to 3 minutes (file uploads, etc.)


async def iosend(io, data):
    #print(f'GEMINI: {data}')
    prompt = data
    api_key = await io.os.get('/etc/gemini')
    api_key = api_key.strip()
    if not api_key:
        await io.error('!! no api key')
        return

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

