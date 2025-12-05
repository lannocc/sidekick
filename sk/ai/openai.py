# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import config
from ..util import play_retry

import openai
import json
import base64
import mimetypes


def _encode_image(image_path: str) -> str:
    """Encodes an image file into a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def _get_mime_type(file_path: str) -> str:
    """Guesses the MIME type of a file."""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type


def prompt_for_text(prompt, chatter=False, model=config.OPENAI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = openai.OpenAI(api_key=config.OPENAI_API_KEY,
                           timeout=config.OPENAI_TIMEOUT_HTTP)
    resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            )
    result_text = resp.choices[0].message.content
    if chatter: print(f'  ai << {result_text}')
    return result_text


def prompt_for_text_stream(prompt, chatter=False, model=config.OPENAI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = openai.OpenAI(api_key=config.OPENAI_API_KEY,
                           timeout=config.OPENAI_TIMEOUT_HTTP)
    stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            )
    for chunk in stream:
        content = chunk.choices[0].delta.content or ""
        if chatter: print(f'  ai << (chunk) {content}')
        yield content


def prompt_for_json(prompt, chatter=False, model=config.OPENAI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = openai.OpenAI(api_key=config.OPENAI_API_KEY,
                           timeout=config.OPENAI_TIMEOUT_HTTP)
    resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            )
    result_text = resp.choices[0].message.content
    if chatter: print(f'  ai << {result_text}')
    return json.loads(result_text)


def prompt_with_file_for_text(prompt, file, chatter=False,
                              model=config.OPENAI_MODEL_SMART_1):
    if chatter: print(f'  ai >> {prompt}')
    client = openai.OpenAI(api_key=config.OPENAI_API_KEY,
                           timeout=config.OPENAI_TIMEOUT_HTTP)

    mime_type = _get_mime_type(file)
    messages = []

    if mime_type and mime_type.startswith('image/'):
        base64_image = _encode_image(file)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
            ]
        })
    else:  # Assume text file
        with open(file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        full_prompt = f"File content:\n\n---\n{file_content}\n---\n\nPrompt:\n{prompt}"
        messages.append({"role": "user", "content": full_prompt})

    resp = client.chat.completions.create(
            model=model,
            messages=messages,
            )

    result_text = resp.choices[0].message.content
    if chatter: print(f'  ai << {result_text}')
    return result_text


def prompt_with_file_for_text_stream(prompt, file, chatter=False,
                                     model=config.OPENAI_MODEL_SMART_1):
    if chatter: print(f'  ai >> {prompt}')
    client = openai.OpenAI(api_key=config.OPENAI_API_KEY,
                           timeout=config.OPENAI_TIMEOUT_HTTP)

    mime_type = _get_mime_type(file)
    messages = []

    if mime_type and mime_type.startswith('image/'):
        base64_image = _encode_image(file)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
            ]
        })
    else:  # Assume text file
        with open(file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        full_prompt = f"File content:\n\n---\n{file_content}\n---\n\nPrompt:\n{prompt}"
        messages.append({"role": "user", "content": full_prompt})

    stream = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True)

    for chunk in stream:
        yield chunk.choices[0].delta.content or ""

def prompt_with_file_for_json(prompt, file, retries=0, quiet=False,
                              chatter=False, model=config.OPENAI_MODEL_SMART_1):
    if chatter: print(f'  ai >> {prompt}')
    client = openai.OpenAI(api_key=config.OPENAI_API_KEY,
                           timeout=config.OPENAI_TIMEOUT_HTTP)

    mime_type = _get_mime_type(file)
    messages = []

    if mime_type and mime_type.startswith('image/'):
        base64_image = _encode_image(file)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}},
            ]
        })
    else:  # Assume text file
        with open(file, 'r', encoding='utf-8') as f:
            file_content = f.read()
        full_prompt = f"File content:\n\n---\n{file_content}\n---\n\nPrompt:\n{prompt}"
        messages.append({"role": "user", "content": full_prompt})

    last_exception = None
    for t in range(retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
            )
            result_text = resp.choices[0].message.content
            if chatter: print(f'  ai << {result_text}')
            return json.loads(result_text)

        except (openai.APIConnectionError, openai.Timeout) as e:
            last_exception = e
            if not quiet: print(f'  -+? RETRY {t+1}')
            play_retry()

    raise last_exception


async def async_prompt_for_text(prompt, chatter=False,
                                model=config.OPENAI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY,
                                timeout=config.OPENAI_TIMEOUT_HTTP)
    resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
    result_text = resp.choices[0].message.content
    if chatter: print(f'  ai << {result_text}')
    return result_text
