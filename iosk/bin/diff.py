# diff.py

import difflib

async def iocall(io, args):
    """Show differences between two text files.

    Usage: diff [-u N] <file1> <file2>
           diff --help

    Options:
      -u N      Unified context lines (default 3)
      --help    Show this help message

    Notes:
      - Files must be text; binary files are refused by the system.
    """
    if args is None:
        await io.error('!! diff: missing arguments')
        return

    tokens = [t for t in args.split(' ') if t]
    if not tokens or '--help' in tokens:
        await io.print(iocall.__doc__)
        return

    context = 3
    i = 0
    while i < len(tokens) and tokens[i].startswith('-') and tokens[i] != '-':
        t = tokens[i]
        if t == '-u':
            i += 1
            if i >= len(tokens):
                await io.error('!! diff: -u requires a number')
                return
            try:
                context = int(tokens[i])
            except ValueError:
                await io.error('!! diff: invalid number for -u')
                return
        elif t == '--help':
            await io.print(iocall.__doc__)
            return
        else:
            await io.error(f'!! diff: unknown option: {t}')
            return
        i += 1

    if len(tokens) - i != 2:
        await io.error('!! diff: requires two file paths')
        return

    f1, f2 = tokens[i], tokens[i+1]

    a = await io.os.get(io, f1)
    if a is None:
        return
    b = await io.os.get(io, f2)
    if b is None:
        return

    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)

    diff = difflib.unified_diff(a_lines, b_lines, fromfile=f1, tofile=f2, n=context)
    output = ''.join(diff)
    if output:
        await io.print(output.rstrip('\n'))
    # If identical, print nothing (like standard diff)
    return True
