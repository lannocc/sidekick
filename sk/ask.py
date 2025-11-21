# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import config
from .ai import google, openai
from .util import get_md_code_block, print_flush as print

import tiktoken

import sys
import time

ENCODING = tiktoken.get_encoding('cl100k_base')


def ask_question(prompt=None, file=None, attachment_content="", mdlang=None,
                 mdsave=None, work_file=None, quiet=False, chatter=False,
                 model=config.GEMINI_MODEL_QUICK_2, use_openai=False):

    if not quiet:
        print('Ask a Question')
        print()

    if attachment_content:
        attachment_bytes = len(attachment_content.encode('utf-8'))
        attachment_tokens = len(ENCODING.encode(attachment_content))
        if not quiet:
            print(f'SUBTOTAL Bytes: {attachment_bytes:,}')
            print(f'SUBTOTAL Tokens: {attachment_tokens:,}')
            print()

    if (mdlang and not mdsave) or (mdsave and not mdlang):
        print('!!! need either both mdlang and mdsave, or neither')
        return

    # Changed: Get prompt from multi-line interactive input or pipe
    if sys.stdin.isatty():
        # Interactive mode
        if not quiet:
            print('    (Ctrl+D to finish)')
            print()
            print(' >> ', end='')
        prompt = sys.stdin.read()
    else:
        # Piped mode
        prompt = sys.stdin.read()

    if not prompt:
        return

    full_text = attachment_content + prompt
    total_bytes = len(full_text.encode('utf-8'))
    total_tokens = len(ENCODING.encode(full_text))

    if work_file:
        try:
            with open(work_file, 'a', encoding='utf-8') as f:
                f.write("--- PROMPT ---\n")
                f.write(prompt)
                f.write("\n\n--- INPUT TOTALS ---\n")
                f.write(f"Bytes: {total_bytes:,}\n")
                f.write(f"Tokens: {total_tokens:,}\n")
        except Exception as e:
            print(f"!!! Error writing prompt to transcript file {work_file}: {e}")
            # Decide if we should continue without the work file.
            # For now, we'll disable it and proceed.
            work_file = None

    if not quiet:
        print()
        print(f'TOTAL INPUT Bytes: {total_bytes:,}')
        print(f'TOTAL INPUT Tokens: {total_tokens:,}')
        print()
        print("...waiting for reply...")

    ai_provider = openai if use_openai else google

    start_time = time.monotonic()
    if file:
        answer = ai_provider.prompt_with_file_for_text(full_text, file, chatter=chatter,
                                              model=model)

    else:
        answer = ai_provider.prompt_for_text(full_text, chatter=chatter, model=model)
    end_time = time.monotonic()
    turnaround_time = end_time - start_time

    output_bytes = len(answer.encode('utf-8'))
    output_tokens = len(ENCODING.encode(answer))

    if work_file:
        try:
            with open(work_file, 'a', encoding='utf-8') as f:
                f.write("\n\n--- ANSWER ---\n")
                f.write(answer)
                f.write("\n\n--- OUTPUT TOTALS ---\n")
                f.write(f"Bytes: {output_bytes:,}\n")
                f.write(f"Tokens: {output_tokens:,}\n")
        except Exception as e:
            print(f"!!! Error writing answer to transcript file {work_file}: {e}")
            work_file = None # Disable further work operations on this file

    summary = None
    answer_for_display = answer
    turnaround_summary_line = f"Turn-around time: {turnaround_time:.2f} seconds"

    if work_file:
        from . import worker
        answer_for_display, summary = worker.do_work(prompt, answer, work_file) # worker will append summary
        try:
            with open(work_file, 'a', encoding='utf-8') as f:
                f.write("\n\n--- PERFORMANCE ---\n")
                f.write(f"{turnaround_summary_line}\n")
        except Exception as e:
            print(f"!!! Error writing performance to transcript file {work_file}: {e}")


    md = None
    if mdlang:
        md = get_md_code_block(mdlang or None, answer)
        if md: answer_for_display = answer.replace(md, '$$$ CODE EXTRACTED $$$')

    print()
    print(f' << {answer_for_display}')
    print()

    if mdsave:
        if md:
            with open(mdsave, 'w') as fout:
                fout.write(md)
                fout.write('\n')
            print(f':: SAVED {mdlang} TO {mdsave}')

        else:
            print(f'!! NO CODE TO SAVE')

    if summary:
        print(summary)
        print()

    if work_file:
        print(f':: Transcript saved to: {work_file}')
        print()

    if not quiet:
        print(f':: Output Bytes: {output_bytes:,}')
        print(f':: Output Tokens: {output_tokens:,}')
        print(f':: {turnaround_summary_line}')
        print()
