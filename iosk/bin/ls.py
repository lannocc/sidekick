import os
import posixpath
from os.path import exists, isdir
#from sk.util import get_ignore_set


async def iocall(io, argv):
    """List directory contents.

    Usage: ls [options] [path ...]
           ls --help

    Options:
      -l        Use a long listing format.
      -a        List all entries, including those starting with '.'.
      -h --help Display this help message.

    [path ...]: The paths to list. If no path is provided use current directory.

    """
    #REMOVED Note: This command honors .skignore files in listed directories.
    long = False
    allp = False

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    paths = [ ]
    for arg in argv:
        if not arg.startswith('-'):
            paths.append(arg)
            continue

        arg = arg[1:]
        for c in arg:
            if c == 'l': long = True
            elif c == 'a': allp = True
            elif c == 'h':
                await io.print(iocall.__doc__)
                return
            else:
                await io.error(f'!! ls: unknown option: -{c}')
                return

    if not paths: paths = [ '' ]
    errors = False
    files = [ ]
    dirs = [ ]

    for path in paths:
        bpath = io.os.box(path, io_context=io)
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

        bpath = io.os.box(path, io_context=io)
        #ignores = get_ignore_set(bpath)
        ignores = set()

        def is_hidden_by_default(item):
            return item.startswith('.') or item.endswith('~') or item == '__pycache__'

        filtered_listing = [
            item for item in listing
            if item not in ignores and (allp or not is_hidden_by_default(item))
        ]

        await io.print(c.join(
            [ f'{file}{"/" if isdir(io.os.box(posixpath.join(path, file), io_context=io)) else ""}'
              for file in filtered_listing ]))

    return not errors

