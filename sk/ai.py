# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT
from .util import play_retry

import google.generativeai as genai0
from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig

from httpx import ReadTimeout, WriteTimeout
import json


model0 = genai0.GenerativeModel(GEMINI_MODEL)


def prompt_for_text(prompt, chatter=False):
    if chatter: print(f'  ai >> {prompt}')
    resp = model0.generate_content(prompt)
    if chatter: print(f'  ai << {resp.text}')
    return resp.text


def prompt_for_json(prompt, chatter=False):
    if chatter: print(f'  ai >> {prompt}')
    resp = model0.generate_content(prompt,
                                  generation_config=genai0.GenerationConfig(
                                      response_mime_type='application/json'))
                                      #timeout=GEMINI_TIMEOUT))
    if chatter: print(f'  ai << {resp.text}')
    return json.loads(resp.text)


def prompt_with_file_for_text(prompt, file, chatter=False):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=GEMINI_API_KEY,
                          http_options=HttpOptions(timeout=GEMINI_TIMEOUT))
    file = client.files.upload(file=file)

    resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                file,
                '\n\n',
                prompt,
            ])

    if chatter: print(f'  ai << {resp.text}')
    return resp.text


def prompt_with_file_for_json(prompt, file, retries=0, quiet=False,
                              chatter=False):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=GEMINI_API_KEY,
                          http_options=HttpOptions(timeout=GEMINI_TIMEOUT))

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
            model=GEMINI_MODEL,
            contents=[
                file,
                '\n\n',
                prompt,
                ],
            config={
                'response_mime_type': 'application/json',
                #'timeout': GEMINI_TIMEOUT,
                })

    if chatter: print(f'  ai << {resp.text}')
    return json.loads(resp.text)


async def async_prompt_for_text(prompt, chatter=False):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=GEMINI_API_KEY,
                          http_options=HttpOptions(timeout=GEMINI_TIMEOUT))

    resp = await client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=['TEXT'],
            ),
        )
    if chatter: print(f'  ai << {resp.text}')
    return resp.text

