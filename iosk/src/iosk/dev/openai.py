# ./src/iosk/dev/openai.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from openai import AsyncOpenAI

# No global client variable.

DEFAULT_MODEL = 'gpt-4o'

async def get_client(io):
    """
    Reads API key from /etc/openai and returns a new AsyncOpenAI client instance.
    This function is called by the kernel to get a client for a device.
    """
    api_key_content = await io.os.get(io, '/etc/openai')
    if not api_key_content:
        # io.os.get already prints a "not found" error.
        await io.error('!! openai: API key file /etc/openai is missing or empty.')
        return None

    api_key = api_key_content.strip()
    if not api_key:
        await io.error('!! openai: API key file /etc/openai contains only whitespace.')
        return None

    return AsyncOpenAI(api_key=api_key)

async def trip(client, prompt, model=DEFAULT_MODEL):
    """
    Performs a round trip using the provided client instance.
    This function is now stateless and relies on the caller to provide the client.
    """
    if not client:
        raise ValueError("OpenAI client is not initialized.")

    # Use the modern API call for chat completions.
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )

    # Correctly parse the response to get the content.
    reply = response.choices[0].message.content
    return reply

async def iosend(io, data):
    """
    Sets up an engagement for the default model.
    Passes a direct reference to the static `trip` function. The Engagement
    class is responsible for calling it with a client and prompt.
    """
    engagement = io.os.chat.engagements.get(io.user)
    if not engagement:
        return
    engagement.append(data, trip)

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
