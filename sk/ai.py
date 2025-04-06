# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT

import google.generativeai as genai0
from google import genai
from google.genai.types import HttpOptions


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


def prompt_with_file_for_json(prompt, file):
    client = genai.Client(api_key=GEMINI_API_KEY,
                          http_options=HttpOptions(timeout=GEMINI_TIMEOUT))
    file = client.files.upload(file=file)

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

