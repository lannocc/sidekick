# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import re


async def iocall(iosk, args):
    #print(f'SKRIP {args}')
    path = args
    file = iosk.box(path)

    with open(file, 'r') as file:
        for line in file:
            line = line.rstrip()
            if not line: continue

            if line.startswith('#'): # comment
                continue

            elif line.startswith('$ '): # command
                #print(f'  SKRIP CMD')
                await iosk.call(line[2:])

            elif re.match(f'^\w+=', line): # variable assignment
                continue # FIXME

            else: # chat
                #print(f'  SKRIP CHAT')
                await iosk.chat.chat(line, cmd=path)

    return True

