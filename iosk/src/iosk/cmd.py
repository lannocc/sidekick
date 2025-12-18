# src/iosk/cmd.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

from . import UNIX
from .io import print_flush as print

import sys
import asyncio
from asyncio.exceptions import CancelledError
import logging
import aioconsole


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
    start_port_num = None
    remaining_args = []
    
    try:
        args_iter = iter(args)
        for arg in args_iter:
            if arg.startswith('-p'):
                port_str = None
                if len(arg) > 2:  # Handles -p4209
                    port_str = arg[2:]
                else:  # Handles -p 4209
                    port_str = next(args_iter)
                
                try:
                    start_port_num = int(port_str)
                except ValueError:
                    raise ValueError(f"invalid port number: '{port_str}'")

                if not (0 < start_port_num < 65536):
                    raise ValueError(f"port number {start_port_num} is out of range")
            elif arg.startswith('-'):
                raise ValueError(f"unrecognized option: {arg}")
            else:
                remaining_args.append(arg)
    except (StopIteration, ValueError) as e:
        error_msg = str(e)
        if isinstance(e, StopIteration):
            error_msg = "option '-p' requires an argument"

        print(f":: error: {error_msg}")
        print("Usage: iosk [-p <port>] <workspace_directory> [<mount_point>]")
        sys.exit(1)

    if not (1 <= len(remaining_args) <= 2):
        print("Usage: iosk [-p <port>] <workspace_directory> [<mount_point>]")
        sys.exit(1)

    # Set the logging level for the google-genai library to WARNING to suppress INFO messages
    #logging.getLogger('google_genai').setLevel(logging.WARNING)
    #logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.disable(logging.INFO) # all INFO and less are disabled

    workspace_directory = remaining_args[0]
    mount_point = remaining_args[1] if len(remaining_args) > 1 else None

    # 2. System Initialization
    print(f'Preparing iosk UNIX at workspace: {workspace_directory}')
    kernel = UNIX(workspace_root=workspace_directory, mount_point=mount_point)
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

        # Start port if requested via command-line argument
        if start_port_num is not None:
            if not hasattr(kernel, 'port') or not kernel.port:
                print(":: warning: port manager subsystem not available, cannot start port.")
            else:
                print(f'Auto-starting network service on port {start_port_num}...')
                if await kernel.port.start(start_port_num):
                    print(f':: port {start_port_num} opened.')
                else:
                    # port.start() already prints a detailed error. This is a fatal startup error.
                    print(f'!! fatal: could not start network service on port {start_port_num}. Shutting down.')
                    if not kernel.halt.is_set():
                        kernel.halt.set()

        # Create a concurrent task for the kernel lifecycle.
        unix_task = asyncio.create_task(kernel.run())

        # This loop manages console sessions. It allows for logging out and then
        # logging back in without shutting down the whole system.
        while not kernel.halt.is_set():
            # --- Phase 1: Active Console Session ---
            # Create and wait for the root console session to complete (i.e., user logs out).
            console_task = asyncio.create_task(_run_console_session(kernel))
            await console_task

            # If the kernel was halted internally (e.g., via the 'halt' command),
            # we should break the loop and proceed to shutdown.
            if kernel.halt.is_set():
                break

            # --- Phase 2: Headless Operation ---
            headless_msg = ':: Press Ctrl+L to log in again, Ctrl+D for graceful shutdown, or Ctrl+C for immediate exit.'
            print('\n:: Root console disconnected. System running in headless mode.')
            print(headless_msg)

            # --- BEGIN FIX: Reset stdin after EOF ---
            # When the interactive session ends due to Ctrl+D (EOF), the standard
            # input stream is marked as closed. To allow reading from the console
            # again in headless mode, we must reset stdin. On POSIX systems, this
            # is done by reopening the controlling terminal. This is a platform-
            # specific workaround for a common TTY behavior.
            if sys.platform != "win32":
                try:
                    sys.stdin.close()
                    sys.stdin = open('/dev/tty')
                except (OSError, ValueError) as e:
                    # This can fail if not attached to a TTY (e.g., in a pipe).
                    # In this non-interactive scenario, we cannot recover and
                    # should proceed with a graceful shutdown.
                    print(f"\n:: warning: could not re-attach terminal ({e}). Shutting down.")
                    if not kernel.halt.is_set():
                        kernel.halt.set()
                    break # Exit the loop.
            # Note: A robust solution for Windows would be needed for full cross-platform
            # support, but this addresses the common case on UNIX-like systems.
            # --- END FIX ---

            try:
                # --- BEGIN FIX: Create and connect a new reader for headless mode ---
                # The previous `reader = asyncio.StreamReader()` was incorrect as it created
                # a reader that was not connected to any input source, causing the program
                # to hang. The correct approach is to create a new asyncio StreamReader and
                # explicitly connect it to the re-opened `sys.stdin`.
                loop = asyncio.get_running_loop()
                reader = asyncio.StreamReader()
                protocol = asyncio.StreamReaderProtocol(reader)
                await loop.connect_read_pipe(lambda: protocol, sys.stdin)
                # --- END FIX ---

                while True:
                    # reader.read(1) returns bytes, so we must compare against bytes literals.
                    char_bytes = await reader.read(1)

                    if not char_bytes:
                        # Ctrl+D was pressed, causing EOF.
                        raise EOFError

                    if char_bytes == b'\x0c': # Ctrl+L
                        # Break this inner loop to re-enter the login session.
                        break
                    elif char_bytes in (b'\r', b'\n'): # Enter
                        # Repeat the help message.
                        print(headless_msg)
                    # All other characters are ignored (hidden).

            except EOFError:
                # Ctrl+D signals a graceful shutdown.
                print('\n:: Graceful shutdown initiated by host signal.')
                if not kernel.halt.is_set():
                    kernel.halt.set()
                break # Exit the loop to proceed with shutdown.

            except KeyboardInterrupt:
                # Ctrl+C signals an immediate shutdown.
                print('\n:: Immediate shutdown initiated by host signal.')
                if not unix_task.done():
                    unix_task.cancel() # Cancel the kernel task immediately.
                break # Exit the loop to proceed with shutdown.

        # --- Shutdown Sequence ---
        # At this point, the loop has exited, and we are shutting down.
        try:
            # We await the unix_task to allow it to clean up.
            # If it was cancelled (Ctrl+C), this will raise CancelledError.
            # If kernel.halt was set (Ctrl+D or 'halt' command), it will complete normally.
            await unix_task
        except CancelledError:
            # This is an expected outcome for an immediate shutdown.
            pass
        finally:
            # A final check to ensure the task is cancelled if it's still running.
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