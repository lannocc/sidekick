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

        pending = {unix_task, console_task}
        
        try:
            # 4. Wait for either task to finish
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED
            )

            # 5. Lifecycle Management
            if console_task in done:
                # The root user logged out. This signals a system shutdown.
                print('\n:: Root console session ended. Initiating system shutdown.')
                kernel.halt.set()
            
        finally:
            # 6. Graceful Shutdown & Cleanup
            # Ensure all tasks are cancelled.
            for task in pending:
                if not task.done():
                    task.cancel()
            
            # Wait for the kernel's shutdown sequence to complete.
            if not unix_task.done():
                try:
                    await unix_task
                except CancelledError:
                    pass # This is expected if it was cancelled.

    # Run the main async loop and handle top-level interruptions
    try:
        asyncio.run(async_run())
    except (KeyboardInterrupt, EOFError):
        print('\n:: Shutdown initiated by user.')
        if kernel and not kernel.halt.is_set():
            kernel.halt.set()

    print("IOSK system has shut down.")

# This simplified structure removes the old SET dictionary and command dispatching.
# The `run` function is now the sole purpose of this module, as per the netroom proposal.
