# search.py

import os
from os.path import isfile, join, relpath
from binaryornot.check import is_binary

async def iocall(io, argv):
    """Search for a term within text files.

    Usage: search [-i] [-n] [-l] [-c] <term> [path ...]
           search --help

    Options:
      -i        Case-insensitive search
      -n        Show line numbers (with normal output)
      -l        List filenames with matches (suppress matched lines)
      -c        Print count of matches per file
      --help    Show this help

    Notes:
      - No quoting is supported; <term> cannot contain spaces.
      - If no paths are provided, defaults to /home/<user> if it exists; otherwise "/".
    """
    if not argv or '--help' in argv:
        await io.print(iocall.__doc__)
        return

    insensitive = False
    show_lineno = False
    list_only = False
    count_only = False

    i = 0
    while i < len(argv) and argv[i].startswith('-') and argv[i] != '-':
        t = argv[i]
        if t == '-i': insensitive = True
        elif t == '-n': show_lineno = True
        elif t == '-l': list_only = True
        elif t == '-c': count_only = True
        elif t == '--help':
            await io.print(iocall.__doc__)
            return
        else:
            await io.error(f'!! search: unknown option: {t}')
            return
        i += 1

    if i >= len(argv):
        await io.error('!! search: <term> required')
        return

    term = argv[i]
    i += 1

    paths = argv[i:]
    # Default search root
    if not paths:
        default_home = f'/home/{io.user}'
        if await io.os.exists(io, default_home):
            paths = [default_home]
        else:
            paths = ['/']

    term_cmp = term.lower() if insensitive else term

    any_errors = False
    any_match = False

    for path in paths:
        if not await io.os.exists(io, path):
            await io.error(f'!! search: path not found: {path}')
            any_errors = True
            continue

        base_fs = io.os.box(path)
        if not os.path.isdir(base_fs):
            # treat as single file
            file_list = [('', os.path.basename(base_fs))]
            walk_iter = [(os.path.dirname(base_fs), [], [os.path.basename(base_fs)])]
        else:
            walk_iter = os.walk(base_fs)

        for root, _dirs, files in walk_iter:
            for name in files:
                fp = join(root, name)
                try:
                    if not isfile(fp):
                        continue
                    # Skip binaries
                    try:
                        if is_binary(fp):
                            continue
                    except Exception:
                        # If detection fails, skip file conservatively
                        continue

                    # Derive iosk path for printing
                    rel = relpath(fp, base_fs) if os.path.isdir(base_fs) else name
                    iosk_path = path if rel in ('', '.') else (join(path, rel))

                    # Read text
                    try:
                        with open(fp, 'r', encoding='utf-8', errors='strict') as f:
                            lines = f.readlines()
                    except UnicodeDecodeError:
                        # Not valid UTF-8 text; skip
                        continue
                    except Exception as e:
                        await io.error(f'!! search: cannot read {iosk_path}: {e}')
                        any_errors = True
                        continue

                    file_count = 0
                    file_listed = False

                    for idx, line in enumerate(lines, start=1):
                        line_cmp = line.lower() if insensitive else line
                        start = 0
                        while True:
                            pos = line_cmp.find(term_cmp, start)
                            if pos == -1:
                                break
                            file_count += 1
                            any_match = True

                            if list_only:
                                if not file_listed:
                                    await io.print(f'{iosk_path}')
                                    file_listed = True
                                break  # for -l, list file once and move to next line

                            if not count_only:
                                if show_lineno:
                                    await io.print(f'{iosk_path}:{idx}:{pos+1}: {line.rstrip()}')
                                else:
                                    await io.print(f'{iosk_path}: {line.rstrip()}')

                            # move past this match
                            start = pos + max(1, len(term_cmp))

                    if count_only and file_count > 0:
                        await io.print(f'{iosk_path}: {file_count}')

                except Exception as e:
                    await io.error(f'!! search: error scanning file: {e}')
                    any_errors = True

    return not any_errors

