# bin/forget.py

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

    # --- BEGIN FIX ---
    # Filter the history in-place by assigning to a slice. This modifies the
    # list object shared by the parent context, rather than just reassigning
    # a local variable in this forked context.
    io.session_history[:] = [
        entry for entry in io.session_history if entry.number not in numbers_to_forget
    ]
    # --- END FIX ---

    removed_count = original_count - len(io.session_history)

    if removed_count == 0:
        await io.print(":: No matching prompt entries found to forget.")
        return True

    # After modifying history, a full recalculation is necessary.
    io.recalculate_token_stats()

    new_token_count = io.token_stats.get('history_tokens', 0)

    await io.print(f":: {removed_count} entries forgotten. History is now {new_token_count} tokens.")

    return True