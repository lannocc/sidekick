import asyncio
from sk.iosk import util

async def iocall(io, argv):
    """Clear the session history (and the screen for console users).

    Usage: clear
           clear --help

    This command clears the entire chat session history,
    leaving only the 'clear' command itself as the first and only entry.
    This effectively provides a clean slate for the session history.

    For interactive console users, this command also clears the screen.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    # --- Bot User Logic: Clear session history and engagement state ---
    
    # 1. Reset the associated Engagement buffers to prevent acting on stale data
    if io.session.user in io.os.chat.engagements:
        engagement = io.os.chat.engagements[io.session.user]
        engagement.buf = None
        engagement.last_buf = None
        engagement.inbuf = None
        engagement.waiting = False
    
    # 2. Reconstruct the session history
    # Get the command that triggered 'clear'
    last_command = ""
    if io.session.history: # command history
        last_command = io.session.history[-1]
    
    # Create the single line of history content that will remain
    new_session_content = f"[{io.session.user}] >> $ {last_command}\n"
    
    # 3. Clear the existing AI history list and reset prompt counter
    io.session.session_history.clear()
    io.session.prompt_number = 1
    
    # 4. Add the new, single entry back into the AI history.
    # This method also correctly increments the prompt number for the next turn.
    io.add_history_entry(new_session_content)

    # 5. Perform a full recalculation of token stats to ensure accuracy,
    # as the history was drastically changed.
    io.recalculate_token_stats()
        
    await io.print(":: session cleared")

    if not io.session.bot:
        # --- Console/Terminal User Logic: Clear the screen ---
        # Use io.output to send the raw escape code without extra formatting
        await io.output(util.ANSI_CLEAR_SCREEN)
    
    return True
