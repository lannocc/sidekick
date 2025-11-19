import asyncio

DOCSTRING = """Remove entries from the session history.

Usage: forget [--help] <id> | <id>-<id> | -<id> | <id>- ...

Removes entries from the session history by their prompt number.
You can specify single numbers, ranges, or a combination.

Examples:
  forget 15          # Forget entry number 15
  forget 15-16       # Forget entries 15 and 16
  forget -10         # Forget all entries up to and including 10
  forget 25-         # Forget all entries from 25 to the most recent
  forget 5 8-12 15   # Forget entry 5, entries 8 through 12, and entry 15
"""

async def iocall(io, argv):
    """Handle the 'forget' command execution."""
    if not argv or '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    numbers_to_forget = set()
    # The current prompt number is the *next* one to be used.
    # The highest existing number is one less.
    max_prompt_number = io.prompt_number - 1

    for arg in argv:
        try:
            if '-' in arg:
                start_str, end_str = arg.split('-', 1)

                start = int(start_str) if start_str else 1
                end = int(end_str) if end_str else max_prompt_number

                if start > end:
                    await io.error(f"!! forget: invalid range '{arg}', start is greater than end.")
                    return False

                numbers_to_forget.update(range(start, end + 1))
            else:
                num = int(arg)
                numbers_to_forget.add(num)
        except ValueError:
            await io.error(f"!! forget: invalid number or range '{arg}'.")
            return False

    if not numbers_to_forget:
        await io.print(":: No valid entries specified to forget.")
        return True

    original_count = len(io.session_history)

    # Filter the history, keeping only entries whose number is not in the set
    io.session_history = [
        entry for entry in io.session_history if entry.number not in numbers_to_forget
    ]

    removed_count = original_count - len(io.session_history)

    if removed_count == 0:
        await io.print(":: No matching history entries found to forget.")
        return True

    # After modifying history, a full recalculation is necessary.
    io.recalculate_token_stats()

    new_token_count = io.token_stats.get('history_tokens', 0)

    await io.print(f":: {removed_count} entries forgotten. History is now {new_token_count} tokens.")

    return True