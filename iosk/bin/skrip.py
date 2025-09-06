import re


async def iocall(io, args):
    """Execute a skrip file or command.

    Usage: skrip <filename>
           skrip -e <command>
           skrip --help

    <filename>: The path to the skrip file to execute.
    -e <command>: Execute the given command string.
    --help: Displays this help message.
    """

    if args == '--help':
        await io.print(iocall.__doc__)
        return

    #print(f'SKRIP {args}')

    if args.startswith('-e '):
        line = args[3:]
        #print(f'SKRIP -e {line}')
        return await handle(io, line)

    path = args
    file = io.os.box(path)

    with open(file, 'r') as file:
        for line in file:
            await handle(io, line)

    return True


async def handle(io, line):
    line = line.rstrip()

    if line.startswith('#'): # comment
        #await io.comment(line)
        pass

    elif line.startswith('$ '): # command
        line = line[2:]

        if re.match(r'^\w+=', line): # variable assignment

            # FIXME
            pass

        else:
            await io.os.call(io, line)

    elif line: # chat (echo)
        #print(f'  SKRIP CHAT')
        #if io.os.chat:
        #    await io.os.chat.chat(line, cmd=path)
        #else:
        #    await io.error('!! no chat')
        await io.print(line)

