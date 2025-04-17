# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT
from .util import play_retry

import google.generativeai as genai0
from google import genai
from google.genai.types import HttpOptions

from httpx import ReadTimeout, WriteTimeout


model0 = genai0.GenerativeModel(GEMINI_MODEL)


def prompt_for_text(prompt):
    resp = model0.generate_content(prompt)
    return resp.text


def prompt_for_json(prompt):
    resp = model0.generate_content(prompt,
                                  generation_config=genai0.GenerationConfig(
                                      response_mime_type='application/json'))
                                      #timeout=GEMINI_TIMEOUT))
    return resp.text


def prompt_with_file_for_text(prompt, file):
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

    return resp.text


def prompt_with_file_for_json(prompt, file, retries=0):
    client = genai.Client(api_key=GEMINI_API_KEY,
                          http_options=HttpOptions(timeout=GEMINI_TIMEOUT))

    for t in range(retries+1):
        try:
            file = client.files.upload(file=file)
            break

        except ReadTimeout:
            print(f'  -+? RETRY {t+1}')

        except WriteTimeout:
            print(f'  -+? RETRY {t+1}')

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

    return resp.text

