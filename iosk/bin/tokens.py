import tiktoken
from os.path import exists

DOCSTRING = """Display detailed token telemetry for the current user session.

Usage: tokens
       tokens --help

This command displays a detailed breakdown of token and byte counts for the
current session, including cumulative totals, last AI trip statistics, and
the current sizes of context components like banked memory and chat history.
This provides the same data visible in the SKYBOARD UI tooltip.
"""

async def iocall(io, argv):
    """
    Calculates and prints the token telemetry for the current user session.
    """
    if '--help' in argv:
        await io.print(DOCSTRING)
        return True

    # DO NOT RECALCULATE; this command is for information only
    #io.recalculate_token_stats()

    # Get the fully updated stats from the user's session.
    stats = io.session.token_stats

    # Prepare data for printing
    lines = [
        ("Cumulative Input", stats['cumulative_input_bytes'], stats['cumulative_input_tokens']),
        ("Cumulative Output", stats['cumulative_output_bytes'], stats['cumulative_output_tokens']),
        ("Last Trip Input", stats['last_trip_input_bytes'], stats['last_trip_input_tokens']),
        ("Last Trip Output", stats['last_trip_output_bytes'], stats['last_trip_output_tokens']),
        ("Banked Memory", stats['banked_bytes'], stats['banked_tokens']),
        ("Session History", stats['history_bytes'], stats['history_tokens']),
        ("Caching Context", stats['caching_context_bytes'], stats['caching_context_tokens']),
    ]

    # Find max label length for alignment
    max_label_len = 0
    if lines:
        max_label_len = max(len(label) for label, _, _ in lines)

    # Print the results
    await io.print("--- Token Telemetry ---")
    for label, byte_count, token_count in lines:
        label_padded = f"{label}:".ljust(max_label_len + 2)
        bytes_str = f"{byte_count:12,d} bytes"
        tokens_str = f"{token_count:12,d} tokens"
        await io.print(f"{label_padded} {bytes_str} | {tokens_str}")

    return True
