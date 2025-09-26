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

    io.os.chat.engagements[io.user].append(prompt, trip)

    if not client:
        client = AsyncClient()

async def iorecv(io):
    if io.user not in io.os.chat.engagements: return None
    data = await io.os.chat.engagements[io.user].input()
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

