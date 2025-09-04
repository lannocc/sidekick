# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

#from openai import OpenAI
from openai import AsyncOpenAI


#MODEL='gpt-3.5-turbo'
MODEL='gpt-4o-mini'

client = None


async def iosend(io, data):
    global client
    #print(f'OPENAI: {data}')
    prompt = data

    io.os.chat.engagements[io.user].append(prompt, trip)

    if not client:
        api_key = await io.os.get(io, '/etc/openai')
        api_key = api_key.strip()
        if not api_key:
            await io.error('!! no api key')
            return

        #client = OpenAI(api_key=api_key)
        client = AsyncOpenAI(api_key=api_key)


async def iorecv(io):
    if io.user not in io.os.chat.engagements: return None
    data = io.os.chat.engagements[io.user].input()
    return data


async def trip(prompt): # round trip
    #print(f'SENDING TO CHATGPT: {prompt}')

    response = await client.responses.create(
        model=MODEL,
        input=prompt,
        store=False,
    )

    reply = response.output_text
    #print(f'GOT CHATGPT REPLY: {reply}')

    return reply

