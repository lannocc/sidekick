# ./src/iosk/dev/ollama.py
from ollama import AsyncClient


DEFAULT_MODEL='gemma3:latest'

# No global client variable.

async def get_client(io):
    """
    Returns a new AsyncClient instance for Ollama.
    This function is called by the kernel to get a client for a device.
    """
    # Ollama client doesn't require API keys or other config from /etc,
    # so we just instantiate it.
    return AsyncClient()

async def trip(client, prompt, model): # round trip
    """
    Performs a round trip using the provided Ollama client instance.
    This function is now stateless and relies on the caller to provide the client and model.
    """
    if not client:
        raise ValueError("Ollama client is not initialized.")

    response = await client.generate(
        model=model,
        prompt=prompt,
    )

    reply = response['response']
    return reply


async def iosend(io, data):
    await iosender(io, data, DEFAULT_MODEL)


async def iosender(io, data, model):
    """
    Sets up an engagement for a specific model.
    Uses a lambda to create a function that has the 'model' argument
    pre-filled. The Engagement class will later call this with (client, prompt).
    """
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return
    model_specific_trip = lambda client, prompt: trip(client, prompt, model=model)
    engagement.append(data, model_specific_trip)

async def iorecv(io, prompt=None):
    """Receives data from the engagement input buffer. Unchanged."""
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return None
    data = await engagement.input()
    return data

