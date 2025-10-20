# src/iosk/cmd.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import UNIX
from .io import print_flush as print

import sys
import asyncio
from asyncio.exceptions import CancelledError
import logging

def run(args=sys.argv[1:]):
    """
    Primary entry point for launching an IOSK system.
    This is now exclusively for launching the local root console.
    """
    # --- BEGIN FIX ---
    # On Windows, the default console may not use UTF-8, causing UnicodeEncodeError
    # when printing characters from other languages. This reconfigures the standard
    # output and error streams to use UTF-8 to prevent this.
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except (TypeError, AttributeError):
            # This is a best-effort fix. In some environments (e.g., older Python
            # versions or when not running in a real console), reconfigure may
            # not be available or may fail.
            print(":: warning: could not reconfigure console to UTF-8.")
    # --- END FIX ---

    # 1. Argument Parsing
    if len(args) != 1 or args[0].startswith('-'):
        print("Usage: iosk <root_directory>")
        sys.exit(1)
    
    # Set the logging level for the google-genai library to WARNING to suppress INFO messages
    #logging.getLogger('google_genai').setLevel(logging.WARNING)
    #logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.disable(logging.INFO) # all INFO and less are disabled
    
    root_directory = args[0]

    # 2. System Initialization
    print(f'Preparing iosk UNIX at root: {root_directory}')
    kernel = UNIX(root=root_directory)
    print('System loaded.')

    # 3. Asynchronous Main Loop
    async def async_run():
        
        # Coroutine for the root user's session lifecycle
        async def _run_console_session(kernel_instance):
            # Login the root user on the default console device.
            io = await kernel_instance.login('root', device='/dev/console')
            if io:
                # Begin the interactive command loop, which blocks until logout.
                await kernel_instance.interactive(io)

        await kernel.start()
        
        # Create concurrent tasks for the kernel lifecycle and the root console session
        unix_task = asyncio.create_task(kernel.run())
        console_task = asyncio.create_task(_run_console_session(kernel))

        # --- Phase 1: Active Console Session ---
        # Wait for the root user to log out (e.g., via 'exit' or Ctrl+D).
        # Ctrl+C is handled within the interactive loop and won't bubble up here.
        await console_task
        
        # --- Phase 2: Headless Operation ---
        print('\n:: Root console disconnected. System running in headless mode.')
        print(':: Press Ctrl+D for graceful shutdown, or Ctrl+C for immediate exit.')
        
        try:
            # The kernel is still running. We wait here for a host signal
            # or for an internal shutdown command to complete the unix_task.
            await unix_task
        except (KeyboardInterrupt, EOFError) as e:
            # This block now ONLY executes after the user has logged out.
            if isinstance(e, EOFError):
                # Ctrl+D: Graceful Shutdown
                print('\n:: Graceful shutdown initiated by host signal.')
                if not kernel.halt.is_set():
                    kernel.halt.set()
                # Wait for kernel to finish its shutdown sequence
                if not unix_task.done():
                    try:
                        await unix_task
                    except CancelledError:
                        pass # This is expected if it was cancelled.
            elif isinstance(e, KeyboardInterrupt):
                # Ctrl+C: Immediate Shutdown
                print('\n:: Immediate shutdown initiated by host signal.')
                if not unix_task.done():
                    unix_task.cancel()
                try:
                    await unix_task # Allow cleanup from cancellation
                except CancelledError:
                    pass
        finally:
            # Final cleanup check
            if not unix_task.done():
                unix_task.cancel()
                try:
                    await unix_task
                except CancelledError:
                    pass

    # Run the main async loop and handle top-level interruptions (e.g., during startup)
    try:
        asyncio.run(async_run())
    except (KeyboardInterrupt, EOFError):
        #print('\n:: Shutdown initiated by user during startup.')
        if kernel and not kernel.halt.is_set():
            kernel.halt.set()

    print("IOSK is done.")

# This simplified structure removes the old SET dictionary and command dispatching.
# The `run` function is now the sole purpose of this module, as per the netroom proposal.

