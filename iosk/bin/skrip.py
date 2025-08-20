# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import re


async def iocall(io, args):
    #print(f'SKRIP {args}')
    path = args
    file = io.os.box(path)

    multi = ''

    with open(file, 'r') as file:
        for line in file:
            line = line.rstrip()
            #if not line: continue

            if line.startswith('#'): # comment
                if multi:
                    await io.os.chat.chat(multi, cmd=path)
                    multi = ''
                continue

            elif line.startswith('$ '): # command
                if multi:
                    await io.os.chat.chat(multi, cmd=path)
                    multi = ''
                #print(f'  SKRIP CMD')
                await io.os.call(line[2:], io=io)

            elif re.match(r'^\w+=', line): # variable assignment
                if multi:
                    await io.os.chat.chat(multi, cmd=path)
                    multi = ''
                continue # FIXME

            else: # chat
                multi += '\n' + line

                #print(f'  SKRIP CHAT')
                #await io.os.chat.chat(line, cmd=path)

        if multi:
            await io.os.chat.chat(multi, cmd=path)

    return True

