import os
from os.path import exists, isdir, join

async def iocall(io, args):
    args = args.split(' ')
    long = False
    allp = False

    paths = [ ]
    for arg in args:
        if not arg.startswith('-'):
            paths.append(arg)
            continue

        arg = arg[1:]
        for c in arg:
            if c == 'l': long = True
            elif c == 'a': allp = True
            else:
                await io.error(f'!! ls: unknown option: -{c}')
                return

    if not paths: paths = [ '' ]
    errors = False
    files = [ ]
    dirs = [ ]

    for path in paths:
        bpath = io.os.box(path)
        if not exists(bpath):
            await io.error(f'!! ls: path does not exist: {path}')
            errors = True

        elif not isdir(bpath): files.append(path)
        else: dirs.append((path, sorted(os.listdir(bpath))))

    c = '\n' if long else '\t'
    if files:
        await io.print(c.join(
            [ file for file in files if allp or not file.startswith('.') ]))

    for path, listing in dirs:
        if (errors or files or len(dirs) > 1):
            await io.print(f'\n{path}:')
        await io.print(c.join(
            [ f'{file}{"/" if isdir(io.os.box(join(path, file))) else ""}'
              for file in listing if allp or not file.startswith('.') ]))

    return not errors

