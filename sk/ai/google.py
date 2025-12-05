# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .. import config
from ..util import play_retry

from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig

from httpx import ReadTimeout, WriteTimeout
import json


def prompt_for_text(prompt, chatter=False, model=config.GEMINI_MODEL_QUICK_2):
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


def _yield_stream_text(resp):
    """
    Try to yield incremental text from different response shapes across
    google-genai versions. If nothing incremental is available, resolve
    and yield the final text once.
    """
    yielded_any = False

    # Some SDK versions return an iterable response, others expose .stream
    iterator = getattr(resp, "stream", resp)

    try:
        for chunk in iterator:
            text = getattr(chunk, "text", None)
            if text:
                yielded_any = True
                yield text
    except TypeError:
        # Not iterable in this version
        pass

    # If no incremental chunks were produced, try to resolve and emit final text
    try:
        if hasattr(resp, "resolve"):
            resp.resolve()
        final_text = getattr(resp, "text", None)
        if final_text and not yielded_any:
            yield final_text
    except Exception:
        # As a last resort, do nothing; caller will handle fallback
        pass


def prompt_for_text_stream(prompt, chatter=False, model=config.GEMINI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))

    # 1) Prefer new streaming API if available
    try:
        if hasattr(client.models, "stream_generate_content"):
            resp = client.models.stream_generate_content(
                model=model,
                contents=prompt,
            )
            for text in _yield_stream_text(resp):
                if chatter: print(f'  ai << (chunk) {text}')
                yield text
            return
    except Exception:
        # Fall through to try older APIs
        pass

    # 2) Try older API that accepted stream=True
    try:
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            stream=True
        )
        for chunk in resp:
            text = getattr(chunk, "text", "") or ""
            if chatter: print(f'  ai << (chunk) {text}')
            if text:
                yield text
        return
    except TypeError:
        # stream kw not supported in this version
        pass
    except Exception:
        # Any other error -> fallback to non-stream
        pass

    # 3) Last resort: non-streaming call, yield once
    text = prompt_for_text(prompt, chatter=chatter, model=model)
    yield text


def prompt_for_json(prompt, chatter=False, model=config.GEMINI_MODEL_QUICK_2):
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
                              model=config.GEMINI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))
    uploaded = client.files.upload(file=file)
    resp = client.models.generate_content(
            model=model,
            contents=[
                uploaded,
                '\n\n',
                prompt,
                ],
            )

    if chatter: print(f'  ai << {resp.text}')
    return resp.text


def prompt_with_file_for_text_stream(prompt, file, chatter=False,
                                     model=config.GEMINI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))
    uploaded = client.files.upload(file=file)

    contents = [uploaded, '\n\n', prompt]

    # 1) Prefer new streaming API if available
    try:
        if hasattr(client.models, "stream_generate_content"):
            resp = client.models.stream_generate_content(
                model=model,
                contents=contents,
            )
            for text in _yield_stream_text(resp):
                if chatter: print(f'  ai << (chunk) {text}')
                yield text
            return
    except Exception:
        pass

    # 2) Try older API that accepted stream=True
    try:
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            stream=True
        )
        for chunk in resp:
            text = getattr(chunk, "text", "") or ""
            if chatter: print(f'  ai << (chunk) {text}')
            if text:
                yield text
        return
    except TypeError:
        pass
    except Exception:
        pass

    # 3) Last resort: non-streaming call, yield once
    text = prompt_with_file_for_text(prompt, file, chatter=chatter, model=model)
    yield text


def prompt_with_file_for_json(prompt, file, retries=0, quiet=False,
                              chatter=False, model=config.GEMINI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))

    for t in range(retries+1):
        try:
            uploaded = client.files.upload(file=file)
            break
        except ReadTimeout:
            if not quiet: print(f'  -+? RETRY {t+1}')
        except WriteTimeout:
            if not quiet: print(f'  -+? RETRY {t+1}')
        play_retry()

    resp = client.models.generate_content(
            model=model,
            contents=[
                uploaded,
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
                                model=config.GEMINI_MODEL_QUICK_2):
    if chatter: print(f'  ai >> {prompt}')
    client = genai.Client(api_key=config.GEMINI_API_KEY,
                          http_options=HttpOptions(
                              timeout=config.GEMINI_TIMEOUT_HTTP))
    resp = await client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=GenerateContentConfig(
                response_modalities=['TEXT'],
            ),
        )
    if chatter: print(f'  ai << {resp.text}')
    return resp.text

