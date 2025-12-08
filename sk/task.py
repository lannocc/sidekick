# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from .action import Context
from .util import play_error, play_success, print_flush as print, count_tokens
from . import agent

from binaryornot.check import is_binary
import tiktoken

import os


def do_task(prompt=None, file=None, attachment_content="", quiet=False,
            chatter=False, model=None, use_openai=False):

    if not quiet:
        print('Perform a Task')
        print()

    if attachment_content:
        attachment_bytes = len(attachment_content.encode('utf-8'))
        attachment_tokens = count_tokens(attachment_content, use_openai=use_openai)
        if not quiet:
            print(f'SUBTOTAL Bytes: {attachment_bytes:,}')
            print(f'SUBTOTAL Tokens: {attachment_tokens:,}')
            print()

    if prompt:
        if not quiet: print(f' >> {prompt}')

    else:
        print(' >> ', end='')
        prompt = input()

    if not prompt:
        return

    full_text = attachment_content + prompt

    if not quiet:
        total_bytes = len(full_text.encode('utf-8'))
        total_tokens = count_tokens(full_text, use_openai=use_openai)
        print(f'TOTAL INPUT Bytes: {total_bytes:,}')
        print(f'TOTAL INPUT Tokens: {total_tokens:,}')
        print()

    context = Context(file)

    try:
        result = agent.just_do_it(context, full_text, quiet=quiet, chatter=chatter)

        if result is not None:
            play_success()
            if not quiet and result.path_name and os.path.exists(result.path_name) and not is_binary(result.path_name):
                with open(result.path_name, 'r', encoding='utf-8') as f:
                    result_content = f.read()
                output_bytes = len(result_content.encode('utf-8'))
                output_tokens = count_tokens(result_content, use_openai=use_openai)
                print()
                print(f':: Total Output Bytes: {output_bytes:,}')
                print(f':: Output Tokens: {output_tokens:,}')
            return result

        else:
            play_error()
            return None

    except Exception as e:
        play_error()
        raise e