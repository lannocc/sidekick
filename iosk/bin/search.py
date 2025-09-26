import os
from os.path import isfile, join, relpath
from binaryornot.check import is_binary

async def iocall(io, argv):
    """Search for a term within text files or stdin.

    Usage: search [-i] [-n] [-l] [-c] <term> [path ...]
           search --help

    Options:
      -i        Case-insensitive search
      -n        Show line numbers
      -l        List filenames with matches only
      -c        Print count of matches per file
      --help    Show this help

    If no paths are given, reads from standard input.
    """
    if not argv or '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    insensitive = False
    show_lineno = False
    list_only = False
    count_only = False

    i = 0
    while i < len(argv) and argv[i].startswith('-') and argv[i] != '-':
        # ... (same option parsing)
        t = argv[i]
        if t == '-i': insensitive = True
        elif t == '-n': show_lineno = True
        elif t == '-l': list_only = True
        elif t == '-c': count_only = True
        else:
            await io.error(f'!! search: unknown option: {t}')
            return False
        i += 1

    if i >= len(argv):
        await io.error('!! search: <term> required')
        return False

    term = argv[i]
    i += 1
    paths = argv[i:]
    term_cmp = term.lower() if insensitive else term

    # Handle stdin if no paths are provided
    if not paths:
        if hasattr(io, 'stdin') and io.stdin:
            content = io.stdin.read()
            lines = content.splitlines()
            any_match = False
            for idx, line in enumerate(lines, start=1):
                line_cmp = line.lower() if insensitive else line
                if term_cmp in line_cmp:
                    any_match = True
                    if show_lineno:
                        await io.print(f"{idx}: {line.rstrip()}")
                    else:
                        await io.print(line.rstrip())
            return any_match
        else:
            # Fallback to default search path if no stdin
            default_home = f'/home/{io.user}'
            if await io.os.exists(io, default_home):
                paths = [default_home]
            else:
                paths = ['/']

    # Existing file search logic
    any_errors = False
    # ... (rest of the file-based search logic remains the same)
    for path in paths:
        if not await io.os.exists(io, path):
            await io.error(f'!! search: path not found: {path}')
            any_errors = True
            continue

        base_fs = io.os.box(path, io_context=io)
        if not os.path.isdir(base_fs):
            walk_iter = [(os.path.dirname(base_fs), [], [os.path.basename(base_fs)])]
        else:
            walk_iter = os.walk(base_fs)

        for root, _dirs, files in walk_iter:
            for name in files:
                fp = join(root, name)
                try:
                    if not isfile(fp) or is_binary(fp): continue

                    rel = relpath(fp, base_fs) if os.path.isdir(base_fs) else name
                    iosk_path = path if rel in ('', '.') else (join(path, rel))

                    try:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                    except Exception:
                        continue

                    file_count = 0
                    file_listed = False

                    for idx, line in enumerate(lines, start=1):
                        line_cmp = line.lower() if insensitive else line
                        if term_cmp in line_cmp:
                            file_count += 1
                            if list_only:
                                if not file_listed:
                                    await io.print(f'{iosk_path}')
                                    file_listed = True
                                break

                            if not count_only:
                                if show_lineno:
                                    await io.print(f'{iosk_path}:{idx}: {line.rstrip()}')
                                else:
                                    await io.print(f'{iosk_path}: {line.rstrip()}')

                    if count_only and file_count > 0:
                        await io.print(f'{iosk_path}: {file_count}')
                except Exception:
                    any_errors = True

    return not any_errors

