# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import config
from .util import play_retry

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig

from httpx import ReadTimeout, WriteTimeout
import json



def prompt_for_text(prompt, chatter=False, model=config.GEMINI_MODEL_SMART):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))
    resp = client.models.generate_content(
            model=model,
            contents=prompt,
            )
    if chatter: print(f'  ai << {resp.text}')
    return resp.text


def prompt_for_json(prompt, chatter=False, model=config.GEMINI_MODEL_SMART):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))
    resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                },
            )
    if chatter: print(f'  ai << {resp.text}')
    return json.loads(resp.text)


def prompt_with_file_for_text(prompt, file, chatter=False,
                              model=config.GEMINI_MODEL_SMART):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))
    file = client.files.upload(file=file)
    resp = client.models.generate_content(
            model=model,
            contents=[
                file,
                '\n\n',
                prompt,
                ],
            )

    if chatter: print(f'  ai << {resp.text}')
    return resp.text


def prompt_with_file_for_json(prompt, file, retries=0, quiet=False,
                              chatter=False, model=config.GEMINI_MODEL_SMART):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))

    for t in range(retries+1):
        try:
            file = client.files.upload(file=file)
            break

        except ReadTimeout:
            if not quiet: print(f'  -+? RETRY {t+1}')

        except WriteTimeout:
            if not quiet: print(f'  -+? RETRY {t+1}')

        play_retry()

    resp = client.models.generate_content(
            model=model,
            contents=[
                file,
                '\n\n',
                prompt,
                ],
            config={
                'response_mime_type': 'application/json',
                },
            )

    if chatter: print(f'  ai << {resp.text}')
    return json.loads(resp.text)


async def async_prompt_for_text(prompt, chatter=False,
                                model=config.GEMINI_MODEL_SMART):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))
    resp = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=['TEXT'],
                # FIXME: timeout???
            ),
        )
    if chatter: print(f'  ai << {resp.text}')
    return resp.text

