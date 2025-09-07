# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

#from openai import OpenAI
from openai import AsyncOpenAI


DEFAULT_MODEL='gpt-4-turbo'

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
    data = io.os.chat.engagements[io.user].input()
    return data


async def online(io):
    global client

    if not client:
        #print('GETTING OPENAI CLIENT')
        api_key = await io.os.get(io, '/etc/openai')
        api_key = api_key.strip()
        if not api_key:
            await io.error('!! no api key')
            return

        #client = OpenAI(api_key=api_key)
        client = AsyncOpenAI(api_key=api_key)


async def trip(prompt, model=DEFAULT_MODEL): # round trip
    #print(f'SENDING TO OPENAI: {prompt}')

    response = await client.responses.create(
        model=model,
        input=prompt,
        store=False,
    )

    reply = response.output_text
    #print(f'GOT OPENAI REPLY: {reply}')

    return reply

