import shlex

DOCSTRING = """Build and execute command lines from standard input.

Usage: ... | xargs [options] [command [initial-arguments]]

Reads items from standard input, delimited by spaces or newlines,
and executes the specified command for each item or group of items.

If no command is given, 'echo' is used by default.

Options:
  -n max-args     Use at most max-args arguments per command line.
  -I replstr      Replace occurrences of replstr in the initial-arguments
                  with names read from standard input. This also implies
                  that the command is executed once for each input item.
                  The options -I and -n are mutually exclusive.
  --help          Display this help message.

Examples:
  # List all python files, then use xargs to run 'describe' on each one.
  $ ls /bin | grep .py$ | xargs describe

  # Find all python files, then use xargs with -I to rename them
  # to have a .bak extension.
  $ ls /bin | grep .py$ | xargs -I {} mv {} {}.bak

  # Create multiple directories at once from a single echo.
  $ echo "dir1 dir2 dir3" | xargs mkdir
"""

async def iocall(io, argv):
    """
    Handles the 'xargs' command execution.
    Parses arguments, reads from stdin, and executes sub-commands.
    """
    if '--help' in argv:
        await io.print(DOCSTRING)
        return True

    if not hasattr(io, 'stdin') or not io.stdin:
        await io.error("!! xargs: requires piped input from stdin")
        return False

    # --- Argument Parsing ---
    max_args = 0  # 0 means no limit, build one big command
    replstr = None
    command_argv = []
    
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == '-n':
            i += 1
            if i >= len(argv):
                await io.error("!! xargs: -n option requires a number")
                return False
            try:
                max_args = int(argv[i])
                if max_args <= 0:
                    await io.error("!! xargs: number for -n must be a positive integer")
                    return False
            except ValueError:
                await io.error(f"!! xargs: invalid number for -n: '{argv[i]}'")
                return False
        elif arg == '-I':
            i += 1
            if i >= len(argv):
                await io.error("!! xargs: -I option requires a replacement string")
                return False
            replstr = argv[i]
        elif arg.startswith('-'):
            await io.error(f"!! xargs: unknown option: {arg}")
            return False
        else:
            # First non-option argument marks the start of the command to be executed
            command_argv = argv[i:]
            break
        i += 1

    if replstr and max_args > 0:
        await io.error("!! xargs: -I and -n options are mutually exclusive")
        return False
    
    if not command_argv:
        # If no command is provided, default to 'echo'
        command_argv = ['echo']

    # --- Read and Process Stdin ---
    stdin_content = io.stdin.read().strip()
    if not stdin_content:
        return True  # Nothing to do, but not an error

    # Use shlex.split to correctly handle items that might be quoted
    items = shlex.split(stdin_content)
    if not items:
        return True

    overall_success = True

    # --- Execution Logic ---
    if replstr is not None:
        # -I mode: execute the command once for each item from stdin
        for item in items:
            # Create a new command by replacing all occurrences of replstr
            current_cmd_argv = [arg.replace(replstr, item) for arg in command_argv]
            cmd_string = shlex.join(current_cmd_argv)
            if not await io.os.call(io, cmd_string):
                overall_success = False

    elif max_args > 0:
        # -n mode: execute the command with chunks of items
        for i in range(0, len(items), max_args):
            chunk = items[i:i + max_args]
            current_cmd_argv = command_argv + chunk
            cmd_string = shlex.join(current_cmd_argv)
            if not await io.os.call(io, cmd_string):
                overall_success = False
    
    else:
        # Default mode: append all items from stdin and execute the command once
        current_cmd_argv = command_argv + items
        cmd_string = shlex.join(current_cmd_argv)
        if not await io.os.call(io, cmd_string):
            overall_success = False

    return overall_success
