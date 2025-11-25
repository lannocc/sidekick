import os
import posixpath
from os.path import exists, isdir, getsize


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
        # Use overlay-aware exists check first
        if not await io.os.exists(io, path):
            await io.error(f'!! ls: path does not exist: {path}')
            errors = True
            continue

        bpath = io.os.box(path, io_context=io)
        if not isdir(bpath):
            try:
                size = getsize(bpath)
            except OSError:
                size = -1
            files.append({'path': path, 'size': size})
        else:
            try:
                # Use the new overlay-aware directory lister, passing the 'show all' flag
                listing = await io.os.list_dir(io, path, show_all=allp, honor_skignore=False)
                dirs.append((path, listing))
            except Exception as e:
                await io.error(f'!! ls: cannot list directory {path}: {e}')
                errors = True

    c = '\n' if long else '\t'
    if files:
        output_items = []
        if long:
            for item in files:
                size = item.get('size', -1)
                size_str = f'{size:10}' if size >= 0 else ' ' * 10
                output_items.append(f"{size_str} {item['path']}")
        else:
            output_items = [item['path'] for item in files]
        
        if output_items:
            await io.print(c.join(output_items))

    for path, listing in dirs:
        if (errors or files or len(dirs) > 1):
            await io.print(f'\n{path}:')

        output_items = []
        if long:
            for item in listing:
                size = item.get('size', -1)
                size_str = f'{size:10}' if size >= 0 else ' ' * 10
                name = f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                output_items.append(f"{size_str} {name}")
        else:
            output_items = [
                f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                for item in listing
            ]
        
        await io.print(c.join(output_items))

    return not errors