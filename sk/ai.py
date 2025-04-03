# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .config import GEMINI_API_KEY, GEMINI_MODEL

import google.generativeai as genai


model = genai.GenerativeModel(GEMINI_MODEL)


def prompt_for_text(prompt):
    resp = model.generate_content(prompt)
    return resp.text


def prompt_for_json(prompt):
    resp = model.generate_content(prompt,
                                  generation_config=genai.GenerationConfig(
                                      response_mime_type='application/json'))
    return resp.text

