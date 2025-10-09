import asyncio

async def iocall(io, argv):
    """Clear the session history for bots or the screen for console users.

    Usage: clear
           clear --help

    For bot users, this command clears the entire chat session history,
    leaving only the 'clear' command itself as the first and only entry.
    This effectively provides a clean slate for the bot's context.

    For interactive console users, this command clears the screen.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if io.bot:
        # --- Bot User Logic: Clear session history and engagement state ---
        
        # 1. Reset the associated Engagement buffers to prevent acting on stale data
        if io.user in io.os.chat.engagements:
            engagement = io.os.chat.engagements[io.user]
            engagement.buf = None
            engagement.last_buf = None
            engagement.inbuf = None
            engagement.waiting = False
        
        # 2. Reconstruct the session history with only the last command
        if io.history:
            last_command = io.history[-1]
            # Recreate the line as it would have been logged in the session
            new_session_content = f"[{io.user}] >> $ {last_command}\n"
            
            # Reset the StringIO object for the session
            io.session.seek(0)
            io.session.truncate(0)
            io.session.write(new_session_content)
        else:
            # Fallback for an empty history: just clear the session
            io.session.seek(0)
            io.session.truncate(0)
            
        await io.print(":: session cleared")

    else:
        # --- Console/Terminal User Logic: Clear the screen ---
        # ANSI escape sequence: \033[H moves cursor to home (top-left)
        #                       \033[2J clears the entire screen
        clear_screen_code = "\033[H\033[2J"
        # Use io.output to send the raw escape code without extra formatting
        await io.output(clear_screen_code)
    
    return True
