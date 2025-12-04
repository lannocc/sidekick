# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import config
from .ai import AIClient
from .util import get_md_code_block, print_flush as print

import tiktoken

import sys
import time
import threading

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

    ai_client = AIClient(use_openai=use_openai)
    start_time = time.monotonic()
    answer = ""

    if quiet:
        print("...waiting for reply...")
        if file:
            answer = ai_client.prompt_with_file_for_text(full_text, file, chatter=chatter, model=model)
        else:
            answer = ai_client.prompt_for_text(full_text, chatter=chatter, model=model)
    else:
        # Streaming with timer for non-quiet mode
        timeout = config.OPENAI_TIMEOUT_HTTP if use_openai else int(config.GEMINI_TIMEOUT_HTTP / 1000)
        stop_timer_event = threading.Event()
        timer_thread = threading.Thread(target=_display_timer, args=(stop_timer_event, timeout))

        answer_chunks = []
        received_first_chunk = False

        try:
            timer_thread.start()
            if file:
                stream = ai_client.prompt_with_file_for_text_stream(full_text, file, chatter=chatter, model=model)
            else:
                stream = ai_client.prompt_for_text_stream(full_text, chatter=chatter, model=model)

            for chunk in stream:
                if not received_first_chunk:
                    received_first_chunk = True
                    stop_timer_event.set()
                    timer_thread.join() # Wait for timer to clear its line
                    print("...Receiving reply...", end="", flush=True)

                answer_chunks.append(chunk)
                if not chatter:
                    print(".", end="", flush=True)

        finally:
            if not received_first_chunk: # If loop never ran (error or empty response)
                stop_timer_event.set()

            if timer_thread.is_alive():
                timer_thread.join()

        if received_first_chunk and not chatter:
            print() # Newline after the dots

        answer = "".join(answer_chunks)

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


def _display_timer(stop_event, timeout):
    """Displays an updating timer on a single line."""
    start_time = time.monotonic()
    max_minutes, max_seconds = divmod(timeout, 60)
    while not stop_event.is_set():
        elapsed = time.monotonic() - start_time
        if elapsed >= timeout:
            break
        minutes, seconds = divmod(int(elapsed), 60)
        # Use \r to overwrite the line. Add padding to clear previous longer lines.
        timer_str = f"...waiting for reply... {minutes:02d}:{seconds:02d} / {int(max_minutes):02d}:{int(max_seconds):02d}"
        print(f"{timer_str.ljust(80)}\r", end='', flush=True)
        time.sleep(0.2)
    print(" " * 80 + "\r", end='', flush=True) # Clear the line when done

