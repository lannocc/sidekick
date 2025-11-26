import os
import posixpath
from os.path import exists, isdir, getsize, getmtime
from datetime import datetime, timedelta


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
      -t        Sort by modification time, newest first.
      -S        Sort by file size, largest first.
      -r, --reverse
                Reverse order while sorting.
      --color   Use color for output.
      --help    Display this help message.

    [path ...]: The paths to list. If no path is provided use current directory.
                Paths can be local or remote (e.g., hostname:/path/).

    """
    #REMOVED Note: This command honors .skignore files in listed directories.
    long = False
    allp = False
    human = False
    show_size = False
    sort_by_time = False
    sort_by_size = False
    reverse = False
    color = False

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
        if arg == '--reverse':
            reverse = True
            continue
        if arg == '--color':
            color = True
            continue

        arg = arg[1:]
        for c in arg:
            if c == 'l': long = True
            elif c == 'a': allp = True
            elif c == 's': show_size = True
            elif c == 'h': human = True
            elif c == 't': sort_by_time = True
            elif c == 'S': sort_by_size = True
            elif c == 'r': reverse = True
            else:
                await io.error(f'!! ls: unknown option: -{c}')
                return

    if not paths: paths = [ '' ]
    errors = False
    files = [ ]
    dirs = [ ]

    for path in paths:
        # To support remote paths, we can't use os.path.isdir.
        # We must try to list the path and, if it fails, treat it as a file.
        try:
            listing = await io.os.list_dir(io, path, show_all=allp, honor_skignore=False)
            if listing is None:
                # A None return from list_dir indicates a network or remote error.
                await io.error(f'!! ls: could not retrieve listing for {path}')
                errors = True
                continue

            # It's a directory. Get its stats if possible (this only works for local paths).
            try:
                bpath = io.os.box(path, io_context=io)
                mtime = getmtime(bpath)
                size = getsize(bpath)
            except OSError:
                mtime = 0
                size = -1
            dirs.append({'path': path, 'listing': listing, 'mtime': mtime, 'size': size})

        except Exception as e:
            # If list_dir raised an exception, it's either a file or an error.
            if 'Not a directory' in str(e):
                # It's a file. Get stats if possible (only works for local paths).
                try:
                    bpath = io.os.box(path, io_context=io)
                    size = getsize(bpath)
                    mtime = getmtime(bpath)
                except OSError:
                    size = -1
                    mtime = 0
                files.append({'path': path, 'size': size, 'mtime': mtime})
            else:
                # It could be a non-existent path or another error. Fallback to `exists` check.
                if not await io.os.exists(io, path):
                    await io.error(f'!! ls: path does not exist: {path}')
                else:
                    await io.error(f'!! ls: cannot access {path}: {e}')
                errors = True


    # Sort files and directories passed as arguments
    if sort_by_time:
        key = lambda x: x.get('mtime', 0)
        order = not reverse
    elif sort_by_size:
        key = lambda x: x.get('size', -1)
        order = not reverse
    else:  # sort by name
        key = lambda x: x['path']
        order = reverse

    files.sort(key=key, reverse=order)
    dirs.sort(key=key, reverse=order)

    # Sort directory contents
    if sort_by_time:
        content_key = lambda x: x.get('mtime', 0)
        content_order = not reverse
    elif sort_by_size:
        content_key = lambda x: x.get('size', -1)
        content_order = not reverse
    else:  # sort by name
        content_key = lambda x: x['name']
        content_order = reverse

    for d in dirs:
        d['listing'].sort(key=content_key, reverse=content_order)


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
                mtime = item.get('mtime', 0)
                mtime_str = format_time(mtime) if mtime > 0 else ' ' * 12
                output_items.append(f"{size_str} {mtime_str} {item['path']}")
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

    C_DIR = '\033[94m'
    C_END = '\033[0m'

    for d in dirs:
        path, listing = d['path'], d['listing']
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
                mtime = item.get('mtime', 0)
                mtime_str = format_time(mtime) if mtime > 0 else ' ' * 12
                name = f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                if color and item['type'] == 'dir':
                    name = f"{C_DIR}{name}{C_END}"
                output_items.append(f"{size_str} {mtime_str} {name}")
        elif show_size:
            for item in listing:
                size = item.get('size', -1)
                prefix = ''
                if size >= 0:
                    size_str = human_size(size) if human else str(size)
                    prefix = f'{size_str} '
                name = f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                if color and item['type'] == 'dir':
                    name = f"{C_DIR}{name}{C_END}"
                output_items.append(f"{prefix}{name}")
        else:
            for item in listing:
                name = f"{item['name']}{'/' if item['type'] == 'dir' else ''}"
                if color and item['type'] == 'dir':
                    name = f"{C_DIR}{name}{C_END}"
                output_items.append(name)
        
        await io.print(c.join(output_items))

    return not errors


def format_time(mtime_timestamp):
    """Formats a timestamp for ls -l output."""
    mtime = datetime.fromtimestamp(mtime_timestamp)
    if datetime.now() - mtime > timedelta(days=180):
        return mtime.strftime('%b %d  %Y')
    else:
        return mtime.strftime('%b %d %H:%M')


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