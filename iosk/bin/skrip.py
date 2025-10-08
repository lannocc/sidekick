import re

async def handle_default_mode(io, line):
    """Handles a line in default skrip mode (chat, comments, '$' commands)."""
    line = line.rstrip()

    if line.startswith('#'):  # Comment
        pass
    elif line.startswith('$ '):  # Command
        command_line = line[2:]
        await handle_shell_mode(io, command_line)
    elif line:  # Chat (echo)
        await io.print(line)

async def handle_shell_mode(io, line):
    """Handles a line in pure shell mode (only comments and commands)."""
    line = line.strip()
    # Ensure the command line is not empty or just a comment
    while line.startswith('$ '): # probably a mistake
        line = line[2:]

    if line and not line.strip().startswith('#'):
        if re.match(r'^\w+=', line): # variable assignment
            try:
                key, value = line.split('=', 1)
                io.env[key] = value
            except ValueError:
                # Failsafe: if split fails, treat as a normal command
                await io.os.call(io, line)
        else:
            await io.os.call(io, line)

async def iocall(io, argv):
    """Execute a skrip file or command.

    Usage: skrip <filename>
           skrip -e <command>
           skrip -s <filename>
           skrip --help

    <filename>: The path to the skrip file to execute in default mode.
                Lines starting with '$ ' are commands; other lines are printed.
    -e <command>: Execute the given command string in default mode.
    -s <filename>: Execute the given file in "pure shell mode". All non-comment
                   lines are treated as commands and do not need a '$ ' prefix.
    --help: Displays this help message.
    """
    if not argv or '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    option = argv[0]

    # Handle '-e' for executing a single command string
    if option == '-e':
        if len(argv) < 2:
            await io.error("!! skrip: -e option requires a command string to execute.")
            return False
        line = ' '.join(argv[1:])
        return await handle_default_mode(io, line)

    # Handle '-s' for pure shell mode file execution
    elif option == '-s':
        if len(argv) != 2:
            await io.error("!! skrip: -s option requires exactly one filename.")
            return False
        path = argv[1]
        try:
            content = await io.os.get(io, path)
            if content is None:
                return False  # Error already printed by io.os.get

            for line in content.splitlines():
                await handle_shell_mode(io, line)
            return True
        except Exception as e:
            await io.error(f"!! skrip: error executing file '{path}' in shell mode: {e}")
            return False

    # Handle unknown options
    elif option.startswith('-'):
        await io.error(f"!! skrip: unknown option '{option}'. Use 'skrip --help'.")
        return False

    # Default behavior: execute a file in skrip mode
    else:
        if len(argv) > 1:
            await io.error("!! skrip: only one filename can be provided for default execution.")
            return False
        path = argv[0]
        try:
            content = await io.os.get(io, path)
            if content is None:
                return False  # Error already printed by io.os.get

            for line in content.splitlines():
                await handle_default_mode(io, line)
            return True
        except Exception as e:
            await io.error(f"!! skrip: error executing file '{path}': {e}")
            return False
