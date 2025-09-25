import re


async def iocall(io, argv):
    """Execute a skrip file or command.

    Usage: skrip <filename>
           skrip -e <command>
           skrip --help

    <filename>: The path to the skrip file to execute.
    -e <command>: Execute the given command string.
    --help: Displays this help message.
    """
    if not argv or '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if argv[0] == '-e':
        if len(argv) < 2:
            await io.error("!! skrip: -e option requires a command to execute.")
            return False
        line = ' '.join(argv[1:])
        return await handle(io, line)

    if len(argv) > 1:
        await io.error("!! skrip: only one filename can be provided.")
        return False

    path = argv[0]
    try:
        content = await io.os.get(io, path)
        if content is None:
            return False # Error already printed by io.os.get

        for line in content.splitlines():
            await handle(io, line)

        return True
    except Exception as e:
        await io.error(f"!! skrip: error executing file '{path}': {e}")
        return False


async def handle(io, line):
    line = line.rstrip()

    if line.startswith('#'): # chat comment
        #await io.comment(line)
        pass

    elif line.startswith('$ '): # command
        line = line[2:]

        if line.startswith('#'): # command comment
            pass

        if re.match(r'^\w+=', line): # variable assignment
            try:
                key, value = line.split('=', 1)
                io.env[key] = value
            except ValueError:
                # Failsafe: if split fails, treat as a normal command
                await io.os.call(io, line)

        else:
            await io.os.call(io, line)

    elif line: # chat (echo)
        #print(f'  SKRIP CHAT')
        #if io.os.chat:
        #    await io.os.chat.chat(line, cmd=path)
        #else:
        #    await io.error('!! no chat')
        await io.print(line)

