import asyncio
import shlex
from datetime import datetime
from io import StringIO
import sys
import os
from sk.iosk import util

DOCSTRING = """Execute a command repeatedly, displaying its output. Console only.

Usage: watch [options] <command>
       watch --help

Executes the specified <command> every N seconds and displays its output
on the screen, clearing the screen before each execution. This is useful
for monitoring changes over time.

This command is only available to users on a console device
(e.g., /dev/console).

Options:
  -n <seconds>   Specify the update interval. The command is executed every
                 <seconds> seconds. The default is 2.0 seconds.
                 Can be used as -n<seconds> or -n <seconds>.
  -c             Enable color. By default, ANSI color escape codes from the
                 command's output are stripped. This option preserves them.
  -h, --help     Display this help message.

To exit, press Ctrl-C, or use the 'kill' command on this process's PID.
"""

async def _wait_for_keypress(loop):
    """Creates a future that completes when a key is pressed on stdin."""
    future = loop.create_future()
    fd = sys.stdin.fileno()

    def on_readable():
        """Callback for when stdin has data."""
        try:
            # Read available bytes to clear the reader event.
            # We don't need the value of the key(s).
            os.read(fd, 1024)
        except Exception:
            pass # Ignore read errors

        if not future.done():
            future.set_result(True)

    loop.add_reader(fd, on_readable)
    try:
        await future
    finally:
        # Crucially, remove the reader when we're done waiting.
        loop.remove_reader(fd)

async def iocall(io, argv):
    """
    Handle the 'watch' command execution.
    """
    # --- 1. Argument Parsing ---
    interval = 2.0
    color_enabled = False
    command_argv = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith('-'):
            if arg in ('-h', '--help'):
                await io.print(DOCSTRING.strip())
                return True
            elif arg == '-c':
                color_enabled = True
            elif arg.startswith('-n'): # Modified to handle -n<seconds> or -n <seconds>
                num_str = None
                if len(arg) > 2: # e.g., "-n10", "-n5.5"
                    num_str = arg[2:]
                else: # arg is exactly "-n", so the number must be the next argument
                    i += 1
                    if i >= len(argv):
                        await io.error("!! watch: -n option requires a number of seconds")
                        return False
                    num_str = argv[i]

                try:
                    interval = float(num_str)
                    if interval <= 0:
                        await io.error("!! watch: interval must be a positive number")
                        return False
                except ValueError:
                    await io.error(f"!! watch: invalid interval '{num_str}'")
                    return False
            else:
                await io.error(f"!! watch: unknown option '{arg}'")
                return False
        else:
            # First non-option argument marks the start of the command
            command_argv = argv[i:]
            break
        i += 1

    if not command_argv:
        await io.error("!! watch: a command to execute is required.")
        await io.print("Usage: watch [options] <command>")
        return False

    command_str = shlex.join(command_argv)

    # --- 2. Device Check ---
    if io.dev not in ('/dev/console', '/dev/terminal'):
        await io.error("!! watch: this command is only available for console users.")
        return False

    # --- 3. Main Loop ---
    loop = asyncio.get_running_loop()

    try:
        await io.output(util.ANSI_HIDE_CURSOR)
        while True:
            # a. Clear the screen and print the header
            await io.output(util.ANSI_CLEAR_SCREEN)
            now_str = datetime.now().strftime('%a %b %d %H:%M:%S %Y')

            # Use a different exit message depending on the console type
            exit_msg = "(Press Ctrl-C to exit)"
            header = f"Every {interval:.1f}s: {command_str} {exit_msg}    {now_str}\n\n"

            await io.output(header)

            # b. Execute the command and capture its output
            watch_io = io.fork()
            watch_io.stdout = StringIO()

            await io.os.call(watch_io, command_str)

            output = watch_io.stdout.getvalue()

            # c. Strip ANSI color codes if -c is not specified
            if not color_enabled:
                output = util.ANSI_ESCAPE_RE.sub('', output)

            # d. Print the captured output
            await io.output(output)

            # e. Wait for the next interval
            # On /dev/console, just sleep and rely on Ctrl-C.
            # The KeyboardInterrupt is handled by the outer try/except block.
            await asyncio.sleep(interval)

    except asyncio.CancelledError:
        # This is the expected interruption from `kill` or `Ctrl+C` (via pipeline).
        # The `finally` block handles all cleanup.
        pass
    finally:
        # This block ensures cleanup happens whether the loop breaks normally
        # (e.g., via keypress) or is cancelled.
        await io.print("\n:: watch terminated.")
        await io.output(util.ANSI_SHOW_CURSOR)

    return True # Indicate graceful exit
