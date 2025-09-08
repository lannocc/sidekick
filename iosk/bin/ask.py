# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import asyncio
import os
import re
from binaryornot.check import is_binary


# This regex utility is commonly used for processing AI responses.
CODEBLOCK_REGEX = re.compile(r'```(?P<language>\w*?)\n(?P<code>.*?)\n```',
                             re.DOTALL)

def get_md_code_block(language, text):
    """Extracts the first code block of a given language from text."""
    matches = CODEBLOCK_REGEX.finditer(text)
    for match in matches:
        lang = match.group('language')
        if language is not None and lang != language:
            continue
        code = match.group('code')
        return code
    return None

async def package_directory(io, path):
    """
    Creates a text representation of a directory and its contents,
    using iosk io primitives.
    """
    text = f"The contents of the directory '{path}' are laid out as follows:\n\n"

    # 1. Get the directory tree structure using the 'tree' command via a staging buffer.
    io.stage_pre()
    try:
        await io.os.call(io, f"tree {path}")
        io.pre.seek(0)
        tree_text = io.pre.read()
        text += tree_text
    except Exception as e:
        await io.error(f"!! ask: failed to generate tree for '{path}': {e}")
        text += f"[Could not generate tree for {path}]\n"
    finally:
        io.stage_normal()

    text += "\n\nThe contents of each file are given below:\n\n"

    # 2. Walk the directory and append file contents.
    root_box = io.os.box(path)
    if not os.path.isdir(root_box):
        await io.error(f"!! ask: path '{path}' is not a directory.")
        return None

    files_to_process = []
    for dirpath, dirnames, filenames in os.walk(root_box):
        # Basic filtering to ignore hidden/temporary files and directories
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        filenames[:] = [f for f in filenames if not (f.startswith('.') or f.endswith('~'))]

        for filename in filenames:
            full_path_box = os.path.join(dirpath, filename)
            files_to_process.append(full_path_box)

    for full_path_box in sorted(files_to_process):
        try:
            if is_binary(full_path_box):
                continue

            # Convert boxed host path back to iosk virtual path for io.os.get()
            iosk_path = '/' + os.path.relpath(full_path_box, io.os.root).replace('\\', '/')
            
            content = await io.os.get(io, iosk_path)
            if content is not None:
                text += f">>> BEGIN FILE .{iosk_path}:\n```\n"
                text += content
                text += "\n```\n<<< END FILE\n\n"
        except Exception as e:
            await io.error(f"!! ask: error processing file '{os.path.basename(full_path_box)}': {e}")
            continue

    return text

async def iocall(io, args):
    """Ask an AI user a question, with optional file/directory context.

    Usage: ask [options] <user> <prompt>
           ask --help

    <user>:   The AI user to ask (e.g., 'openai', 'google').
    <prompt>: The question or instruction for the AI.

    Options:
      -d <device>         Specify a specific device model (e.g., 'openai/gpt-4o').
                          Defaults to the user's current device.
      -f <file>           Attach a single file's content to the prompt.
      -p <directory>      Package a directory's contents and attach to the prompt.
      -e <lang> <file>    Extract a markdown code block of <lang> from the
                          response and save it to <file>.
      --help              Display this help message.

    Note: The screenshot option (-s) is not available in the iosk environment.
          Only one of -f or -p can be used at a time.
    """
    if not args or '--help' in args:
        await io.print(iocall.__doc__)
        return

    args_list = [a for a in args.split(' ') if a]
    options = {}
    user = None
    prompt_parts = []
    
    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg in ['-d', '-f', '-p']:
            if i + 1 >= len(args_list):
                await io.error(f"!! ask: option '{arg}' requires an argument.")
                return
            options[arg[1]] = args_list[i+1]
            i += 2
        elif arg == '-e':
            if i + 2 >= len(args_list):
                await io.error("!! ask: option '-e' requires <language> and <file> arguments.")
                return
            options['e_lang'] = args_list[i+1]
            options['e_file'] = args_list[i+2]
            i += 3
        elif not user:
            user = arg
            i += 1
        else:
            prompt_parts.append(arg)
            i += 1

    prompt = ' '.join(prompt_parts)

    if not user:
        await io.error("!! ask: missing <user> argument.")
        return
    if not prompt:
        await io.error("!! ask: missing <prompt> argument.")
        return
    if 'f' in options and 'p' in options:
        await io.error("!! ask: cannot use both -f and -p options at the same time.")
        return
    if user not in io.os.users:
        await io.error(f"!! ask: user '{user}' is not online.")
        return
    
    target_io = io.os.users[user]
    if not target_io.bot:
        await io.error(f"!! ask: user '{user}' is not an AI bot.")
        return

    attachment = ""
    if 'f' in options:
        filepath = options['f']
        await io.print(f":: Attaching file: {filepath}")
        content = await io.os.get(io, filepath)
        if content is None: return
        attachment = f"Please consider the following file content from '{filepath}':\n\n---\n{content}\n---\n\n"
    elif 'p' in options:
        dirpath = options['p']
        await io.print(f":: Packaging and attaching directory: {dirpath}")
        content = await package_directory(io, dirpath)
        if content is None: return
        attachment = f"Please consider the following directory structure and file contents from '{dirpath}':\n\n{content}\n\n"

    final_prompt = attachment + prompt
    device = options.get('d')
    if device:
        device = os.path.join('/dev', device).replace('\\','/')
        if not await io.os.exists(io, device):
            await io.error(f"!! ask: specified device does not exist: {device}")
            return
    else:
        device = target_io.dev

    await io.print(f":: Asking '{user}' via device '{device}'...")
    await io.os.send(target_io, device, final_prompt)
    
    response = None
    timeout_seconds = 180 # 3 minute timeout
    start_time = asyncio.get_event_loop().time()
    while response is None:
        if (asyncio.get_event_loop().time() - start_time) > timeout_seconds:
            await io.error(f"!! ask: timed out waiting for a response from '{user}'.")
            return
        response = await io.os.recv(target_io, device)
        if response is None:
            await asyncio.sleep(0.5)

    if 'e_lang' in options:
        lang = options['e_lang']
        save_path = options['e_file']
        code = get_md_code_block(lang, response)
        
        if code:
            try:
                boxed_path = io.os.box(save_path)
                with open(boxed_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                response = response.replace(f"```{lang}\n{code}\n```", f"\n:: Code extracted to '{save_path}'\n")
                await io.print(f":: Saved {lang} code block to {save_path}")
            except Exception as e:
                await io.error(f"!! ask: failed to write to file '{save_path}': {e}")
        else:
            await io.print(f":: No '{lang}' code block found to extract.")

    await io.print("\n-- Response from " + user + " --")
    await io.print(response.strip())
    
    return True
