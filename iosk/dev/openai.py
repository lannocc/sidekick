# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from openai import OpenAI


#MODEL='gpt-3.5-turbo'
MODEL='gpt-4o-mini'


async def iosend(io, data):
    #print(f'OPENAI: {data}')
    prompt = data
    api_key = await io.os.get(io, '/etc/openai')
    api_key = api_key.strip()
    if not api_key:
        await io.error('!! no api key')
        return

    client = OpenAI(api_key=api_key)
    #resp = client.chat.completions.create(
    #        model=MODEL,
    #        messages=[
    #            { 'role': 'user', 'content': prompt },
    #        ])
    #
    #return resp.choices[0].message.content

    response = client.responses.create(
        model=MODEL,
        input=prompt,
        store=False,
    )

    return response.output_text

