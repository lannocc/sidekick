# ./src/iosk/dev/google.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig

# No global client variable.

DEFAULT_MODEL = 'gemini-2.5-flash'
TIMEOUT = 3 * 60 * 1000 # wait up to 3 minutes (file uploads, etc.)

async def get_client(io):
    """
    Reads API key from /etc/google and returns a new genai.Client instance.
    This function is called by the kernel to get a client for a device.
    """
    api_key_content = await io.os.get(io, '/etc/google')
    if not api_key_content:
        # io.os.get already prints a "not found" error.
        await io.error('!! google: API key file /etc/google is missing or empty.')
        return None

    api_key = api_key_content.strip()
    if not api_key:
        await io.error('!! google: API key file /etc/google contains only whitespace.')
        return None

    return genai.Client(api_key=api_key, http_options=HttpOptions(timeout=TIMEOUT))

async def trip(client, prompt, model=DEFAULT_MODEL):
    """
    Performs a round trip using the provided client instance.
    This function is now stateless and relies on the caller to provide the client.
    """
    if not client:
        raise ValueError("Google client is not initialized.")

    resp = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=GenerateContentConfig(
            response_modalities=['TEXT'],
        ),
    )

    return resp.text

async def iosend(io, data):
    """
    Sets up an engagement for the default model.
    Passes a direct reference to the static `trip` function. The Engagement
    class is responsible for calling it with a client and prompt.
    """
    engagement = io.os.chat.engagements.get(io.session.user)
    if not engagement:
        return
    engagement.append(data, trip)

async def iosender(io, data, model):
    """
    Sets up an engagement for a specific model.
    Uses a lambda to create a function that has the 'model' argument
    pre-filled. The Engagement class will later call this with (client, prompt).
    """
    engagement = io.os.chat.engagements.get(io.session.user)
    if not engagement:
        return
    model_specific_trip = lambda client, prompt: trip(client, prompt, model=model)
    engagement.append(data, model_specific_trip)

async def iorecv(io, prompt=None):
    """Receives data from the engagement input buffer. Unchanged."""
    engagement = io.os.chat.engagements.get(io.session.user)
    if not engagement:
        return None
    data = await engagement.input()
    return data
