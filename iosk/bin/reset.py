import asyncio

DOCSTRING = """Reset a user's session to a clean state.

Usage: reset [username]
       reset --help

Clears session history, command history, loaded banks, environment variables,
aliases, and resets the current working directory to the user's home.
Then, it re-runs the system-wide /etc/skrc and the user's ~/.skrc file,
simulating a fresh login.

If no username is provided, it resets the current user's session.
Only superusers can reset the session of another user.
"""

async def iocall(io, argv):
    """Handle the 'reset' command execution."""
    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if len(argv) > 1:
        await io.error("!! reset: too many arguments. Usage: reset [username]")
        return False

    target_user_name = argv[0] if argv else io.user

    # --- Permission Check ---
    if target_user_name != io.user and not io.su:
        await io.error("!! reset: permission denied. Only superusers can reset other users.")
        return False

    # --- Target User Validation ---
    if target_user_name not in io.os.users:
        await io.error(f"!! reset: user '{target_user_name}' not found.")
        return False

    target_io = io.os.users[target_user_name]

    await io.print(f":: resetting session for user '{target_user_name}'...")

    # Inform the target user if they were reset by someone else
    if io.user != target_user_name:
        await target_io.print(f":: your session has been reset by administrator '{io.user}'.")

    # --- 1. Clear all session state ---

    # --- History Proposal Implementation ---
    # Clear structured chat history, reset prompt number and rolling config
    target_io.session_history.clear()
    target_io.prompt_number = 1
    target_io.rolling_config = {'enabled': False, 'mode': None, 'limit': 0}
    # target_io.session.seek(0) # REPLACED
    # target_io.session.truncate(0) # REPLACED
    # --- End Implementation ---

    # Clear engagement buffers (for bots)
    if target_io.bot and target_user_name in io.os.chat.engagements:
        engagement = io.os.chat.engagements[target_user_name]
        engagement.buf = None
        engagement.last_buf = None
        engagement.inbuf = None
        engagement.waiting = False

    # Clear command history, banks, env vars, and aliases
    target_io.history.clear()
    target_io.banks.clear()
    target_io.env.clear()
    target_io.aliases.clear()

    # Reset token counts and preamble cache
    target_io.preamble_cache = None
    # --- History Proposal Implementation ---
    # Trigger a full recalculation of token stats after clearing everything.
    target_io.recalculate_token_stats()
    # --- End Implementation ---


    # --- BEGIN FIX ---
    # Reset Current Working Directory, correctly handling the 'root' user.
    if target_user_name == 'root':
        home_dir = '/root'
    else:
        home_dir = f'/home/{target_user_name}'
    target_io.pwd = home_dir
    # --- END FIX ---

    # --- 2. Re-initialize the session ---

    # Re-run preamble/postamble setup and token calculation for chat context
    if io.os.chat and hasattr(io.os.chat, '_setup_chat_context'):
        await io.os.chat._setup_chat_context(target_io)

    # Re-run system-wide skrc
    skrc_global_path = '/etc/skrc'
    if await io.os.exists(target_io, skrc_global_path):
        await io.os.exec(target_io, skrc_global_path)

    # --- BEGIN FIX ---
    # Re-run user-specific .skrc, using the correctly determined home directory.
    skrc_user_path = f'{home_dir}/.skrc'
    # --- END FIX ---
    if await io.os.exists(target_io, skrc_user_path):
        await io.os.exec(target_io, skrc_user_path)

    # --- 3. Final Notification ---

    # Inform the command issuer
    await io.print(f":: session for user '{target_user_name}' has been reset.")

    return True