# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import re


async def iocall(io, args):
    #print(f'SKRIP {args}')

    if args.startswith('-e '):
        line = args[3:]
        #print(f'SKRIP -e {line}')
        return await handle(io, line)

    path = args
    file = io.os.box(path)

    multi = ''

    with open(file, 'r') as file:
        for line in file:
            line = line.rstrip()
            #if not line: continue

            if line.startswith('#'): # comment
                if multi:
                    #if io.os.chat: await io.os.chat.chat(multi, cmd=path)
                    await io.print(multi)
                    multi = ''

            elif line.startswith('$ '): # command
                if multi:
                    #if io.os.chat: await io.os.chat.chat(multi, cmd=path)
                    await io.print(multi)
                    multi = ''
                #print(f'  SKRIP CMD')
                await io.os.call(io, line[2:])

            elif re.match(r'^\w+=', line): # variable assignment
                if multi:
                    #if io.os.chat: await io.os.chat.chat(multi, cmd=path)
                    await io.print(multi)
                    multi = ''

            else: # chat
                multi += '\n' + line

                #print(f'  SKRIP CHAT')
                if io.os.chat:
                    await io.os.chat.chat(line, cmd=path)
                else:
                    await io.error('!! no chat')

        if multi:
            #if io.os.chat: await io.os.chat.chat(multi, cmd=path)
            await io.print(multi)

    return True


async def handle(io, line):
    line = line.rstrip()

    if line.startswith('#'): # comment
        pass

    elif line.startswith('$ '): # command
        await io.os.call(io, line[2:])

    elif re.match(r'^\w+=', line): # variable assignment

        # FIXME
        pass

    elif line: # chat
        #print(f'  SKRIP CHAT')
        if io.os.chat:
            await io.os.chat.chat(line, cmd=path)
        else:
            await io.error('!! no chat')

