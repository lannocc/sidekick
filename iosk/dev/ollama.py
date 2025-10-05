# ./dev/ollama.py
from ollama import AsyncClient

#MODEL='deepseek-r1'
#MODEL='deepseek-coder'
#MODEL='codellama'
MODEL='gemma3'

client = None

async def iosend(io, data):
    global client
    #print(f'OLLAMA: {data}')
    prompt = data

    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return None
    engagement.append(prompt, trip)

    if not client:
        client = AsyncClient()

async def iorecv(io, prompt=None):
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return None
    data = await engagement.input()
    return data

async def trip(prompt): # round trip
    #print(f'SENDING TO OLLAMA: {prompt}')

    response = await client.generate(
        model=MODEL,
        prompt=prompt,
    )

    reply = response['response']
    #print(f'GOT OLLAMA REPLY: {reply}')

    return reply

