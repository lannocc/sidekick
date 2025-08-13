# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@


async def iocall(iosk, args):
    path = args
    file = iosk.box(path)

    with open(file, 'r') as file:
        for line in file:
            line = line.rstrip()
            if not line: continue

            if line.startswith('#'): # comment
                continue

            elif line.startswith('$ '): # command
                await iosk.call(line[2:])

            else: # chat
                await iosk.chat.chat(line)

    return True

