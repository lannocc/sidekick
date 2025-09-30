import tiktoken
from os.path import exists

DOCSTRING = """Calculate token usage for the current session context.

Usage: tokens
       tokens --help

This command assembles the full context that would be sent to an AI, including
the preamble, banked memory, chat history, and postamble, and reports its size.
It also displays two running totals for the entire session:
- Session Total (caching): Simulates a caching model where the static preamble
  and banked memory are counted once, and each subsequent AI trip adds only the
  dynamic chat history and postamble.
- Session Total (cumulative): A full cumulative total, where each AI trip adds
  the token count of the entire context (static + dynamic).
"""

async def iocall(io, argv):
    """
    Calculates and prints the total bytes and estimated token count for the current
    user's full session context (preamble, banks, history, postamble), as well
    as session-long running totals.
    """
    if '--help' in argv:
        await io.print(DOCSTRING)
        return True

    # Use a forked context to capture script outputs without polluting the main session's stdout
    temp_io = io.fork()

    # --- 1. Get Preamble Content ---
    preamble_content = io.preamble_cache or ""

    # --- 2. Get Banked Memory Content ---
    banking_content = ""
    if io.banks:
        for bank_acct, data in io.banks.items():
            banking_content += '\n' + data + '\n'

        if banking_content:
            banking_content = (
                '\n=== CORE RULES/MEMORY BEGIN ===\n'
                'THIS SECTION IS MOST IMPORTANT, I MUST ALWAYS REMEMBER:\n'
                f'{banking_content}'
                '\n=== END   CORE RULES/MEMORY ===\n'
            )

    # --- 3. Get Chat History Content ---
    io.session.seek(0)
    chat_history_content = io.session.read()

    # --- 4. Get Postamble Content ---
    postamble_content = ""
    postamble_path = '/etc/chat/postamble'
    try:
        # Re-use the forked context for postamble capture
        temp_io.stage_post()
        if await temp_io.os.exists(temp_io, postamble_path):
            await temp_io.os.exec(temp_io, postamble_path)

        if temp_io.post:
            temp_io.post.seek(0)
            postamble_content = temp_io.post.read()
    finally:
        temp_io.stage_normal()

    # --- 5. Assemble the Full Context String ---
    full_context = (
        preamble_content +
        banking_content +
        '\n=== IOSK PERSONAL CHAT HISTORY BEGIN ===\n' +
        chat_history_content +
        '\n=== END   IOSK PERSONAL CHAT HISTORY ===\n\n' +
        postamble_content
    )

    # --- 6. Calculate Bytes and Tokens ---
    try:
        data_bytes = full_context.encode('utf-8')
        byte_count = len(data_bytes)

        encoding = tiktoken.get_encoding('cl100k_base')
        tokens = encoding.encode(full_context)
        token_count = len(tokens)
    except Exception as e:
        await io.error(f"!! tokens: failed during calculation: {e}")
        return False

    # --- 7. Print the Results ---
    await io.print(f' Bytes this trip: {byte_count:,}')
    await io.print(f'Tokens this trip: {token_count:,}')
    await io.print(f'Tokens session total (caching on): {io.caching_token_total:,}')
    await io.print(f'Tokens session total (cumulative): {io.full_token_total:,}')

    return True

