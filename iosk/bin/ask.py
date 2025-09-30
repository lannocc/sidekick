import os
from sk.util import package_directory, get_md_code_block
from sk.iosk.dev.google import online as google_online, trip as google_trip

DOCSTRING = """Ask an AI a question, with optional file/directory context.

Usage: ask [options] <prompt>
       ask --help

If <prompt> is not provided as an argument, it is read from standard input.

Options:
  -h, --help        Displays this help message.
  -q, --quiet       Quiet mode. Only print the final AI response.
  -f <file>         Attach the contents of the specified file to the prompt.
                    Can be specified multiple times.
  -p <directory>    Package and attach the contents of the specified directory.
                    Can be specified multiple times.
  -e <lang> <file>  Extract the first markdown code block of <lang> from the
                    response and save it to <file>.
  -1                Use model: gemini-2.0-flash-lite.
  -2                Use model: gemini-2.5-flash (default).
  -3                Use model: gemini-2.5-pro.
"""

async def iocall(io, argv):
    """
    Handle the 'ask' command execution.
    This function parses arguments, constructs a prompt, interacts with the AI,
    and handles the response.
    """
    if '--help' in argv or '-h' in argv:
        await io.print(DOCSTRING.strip())
        return True

    files_to_attach = []
    paths_to_package = []
    extract_lang = None
    extract_file = None
    model = 'gemini-2.5-flash'
    quiet_mode = False
    prompt_args = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith('-'):
            if arg == '-f':
                i += 1
                if i >= len(argv):
                    await io.error("!! ask: -f requires a filename.")
                    return False
                files_to_attach.append(argv[i])
            elif arg == '-p':
                i += 1
                if i >= len(argv):
                    await io.error("!! ask: -p requires a directory path.")
                    return False
                paths_to_package.append(argv[i])
            elif arg == '-e':
                i += 1
                if i >= len(argv):
                    await io.error("!! ask: -e requires <lang> and <file> arguments.")
                    return False
                extract_lang = argv[i]
                i += 1
                if i >= len(argv):
                    await io.error("!! ask: -e requires <file> argument after <lang>.")
                    return False
                extract_file = argv[i]
            elif arg == '-1':
                model = 'gemini-2.0-flash-lite'
            elif arg == '-2':
                model = 'gemini-2.5-flash'
            elif arg == '-3':
                model = 'gemini-2.5-pro'
            elif arg in ('-q', '--quiet'):
                quiet_mode = True
            else:
                await io.error(f"!! ask: unknown option: {arg}")
                return False
        else:
            prompt_args.append(arg)
        i += 1

    prompt = ' '.join(prompt_args)
    if not prompt:
        if hasattr(io, 'stdin') and io.stdin:
            prompt = io.stdin.read().strip()
            if not prompt:
                await io.error("!! ask: prompt required, and stdin was empty.")
                return False
        else:
            await io.error("!! ask: prompt required.")
            return False
        
    # --- Prompt Construction ---
    ask_io = io.fork()
    
    preamble_content = ""
    try:
        ask_io.stage_pre()
        await ask_io.os.exec(ask_io, '/etc/ask/preamble')
        if ask_io.pre:
            ask_io.pre.seek(0)
            preamble_content = ask_io.pre.read()
    finally:
        ask_io.stage_normal()

    attachment_content = ""
    for file_path in files_to_attach:
        content = await io.os.get(io, file_path)
        if content is None: return False
        attachment_content += f"\n--- ATTACHED FILE: {file_path} ---\n{content}"

    if paths_to_package:
        host_paths = [io.os.box(p, io_context=io) for p in paths_to_package]
        packaged_filepath_host, counts = package_directory(host_paths)

        if not quiet_mode:
            if isinstance(counts, list):
                for i, count_str in enumerate(counts):
                    await io.print(count_str.strip())
                    await io.print(paths_to_package[i])
            else:
                await io.print(counts.strip())
                await io.print(paths_to_package[0])

        with open(packaged_filepath_host, 'r', encoding='utf-8') as f:
            packaged_content = f.read()
        os.remove(packaged_filepath_host)
        
        if attachment_content:
            attachment_content += "\n" + packaged_content
        else:
            attachment_content = packaged_content

    postamble_content = ""
    try:
        ask_io.stage_post()
        await ask_io.os.exec(ask_io, '/etc/ask/postamble')
        if ask_io.post:
            ask_io.post.seek(0)
            postamble_content = ask_io.post.read()
    finally:
        ask_io.stage_normal()
        
    full_prompt = (
        preamble_content +
        attachment_content +
        "\n--- USER PROMPT ---\n" +
        prompt + "\n" +
        postamble_content
    )

    # --- AI Interaction ---
    try:
        await google_online(io)
        if not quiet_mode:
            await io.print(f":: asking {model}...")
        response = await google_trip(prompt=full_prompt, model=model)
    except Exception as e:
        await io.error(f"!! ask: AI interaction failed: {e}")
        return False

    # --- Output Handling ---
    if not response:
        if not quiet_mode:
            await io.print(":: AI returned no response.")
        return True

    final_response = response
    
    if extract_lang and extract_file:
        code_block = get_md_code_block(extract_lang, response)
        if code_block:
            host_path = io.os.box(extract_file, io_context=io)
            try:
                with open(host_path, 'w', encoding='utf-8') as f:
                    f.write(code_block)
                if not quiet_mode:
                    await io.print(f":: extracted '{extract_lang}' code to {extract_file}")
                final_response = response.replace(code_block, f"...\n[Code extracted to {extract_file}]\n...")
            except Exception as e:
                await io.error(f"!! ask: failed to save extracted code to {extract_file}: {e}")
        else:
            if not quiet_mode:
                await io.print(f":: no '{extract_lang}' code block found to extract.")
            
    if not quiet_mode:
        await io.print("\n--- RESPONSE ---")
    
    await io.print(final_response.strip())
    
    return True
