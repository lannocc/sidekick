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
      -s, --size  Show file sizes.
      -h, --human-readable
                With -l or -s, print sizes in human-readable format (e.g., 1K 234M 2G).
      --help    Display this help message.

    [path ...]: The paths to list. If no path is provided use current directory.

    """
    #REMOVED Note: This command honors .skignore files in listed directories.
    long = False
    allp = False
    human = False
    show_size = False

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    paths = [ ]
    for arg in argv:
        if not arg.startswith('-'):
            paths.append(arg)
            continue

        if arg == '--size':
            show_size = True
            continue
        if arg == '--human-readable':
            human = True
            continue

        arg = arg[1:]
        for c in arg:
            if c == 'l': long = True
            elif c == 'a': allp = True
            elif c == 's': show_size = True
            elif c == 'h': human = True
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
                if human:
                    size_str = f'{human_size(size):>10}'
                else:
                    size_str = f'{size:10}' if size >= 0 else ' ' * 10
                output_items.append(f"{size_str} {item['path']}")
        elif show_size:
            for item in files:
                size = item.get('size', -1)
                prefix = ''
                if size >= 0:
                    size_str = human_size(size) if human else str(size)
                    prefix = f'{size_str} '
                output_items.append(f"{prefix}{item['path']}")
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
                if human:
                    size_str = f'{human_size(size):>10}'
                else:
                    size_str = f'{size:10}' if size >= 0 else ' ' * 10
                name = f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                output_items.append(f"{size_str} {name}")
        elif show_size:
            for item in listing:
                size = item.get('size', -1)
                prefix = ''
                if size >= 0:
                    size_str = human_size(size) if human else str(size)
                    prefix = f'{size_str} '
                name = f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                output_items.append(f"{prefix}{name}")
        else:
            output_items = [
                f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                for item in listing
            ]
        
        await io.print(c.join(output_items))

    return not errors


def human_size(size_bytes):
    """Converts a size in bytes to a human-readable string."""
    if size_bytes < 0:
        return ''
    if size_bytes == 0:
        return '0'

    power = 1024.0
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    size_float = float(size_bytes)
    while size_float >= power and n < len(power_labels) - 1:
        size_float /= power
        n += 1

    if n == 0:
        return str(size_bytes)

    return f'{size_float:.1f}{power_labels[n]}'