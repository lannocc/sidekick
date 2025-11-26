# describe.py

import os
from os.path import exists, isfile, isdir, getsize, splitext, basename
from binaryornot.check import is_binary
import json
import ast

async def iocall(io, argv): # Changed 'args' to 'argv'
    """Describe a file or directory.

    Usage: describe <path>
           describe --help

    Provides a concise summary: type, size, line/word counts for text, simple type heuristics.
    """
    if not argv or '--help' in argv: # Updated check for empty argv or --help
        await io.print(iocall.__doc__)
        return

    path = argv[0]

    # Use overlay-aware exists to respect tombstones
    if not await io.os.exists(io, path):
        await io.error(f'!! describe: path not found: {path}')
        return

    # Once we know it exists, box it to get the host path for reading
    box = io.os.box(path, io_context=io)

    if isdir(box):
        try:
            # Use overlay-aware list_dir for merged view
            listing = await io.os.list_dir(io, path)
        except Exception as e:
            await io.error(f'!! describe: cannot list directory: {e}')
            return

        files = sum(1 for item in listing if item['type'] == 'file')
        dirs = sum(1 for item in listing if item['type'] == 'dir')
        await io.print(f'Path: {path}')
        await io.print('Type: directory')
        await io.print(f'Items: {len(listing)} (files: {files}, dirs: {dirs})')
        return True

    # File
    try:
        if is_binary(box):
            size = getsize(box)
            ext = splitext(path)[1].lower()
            await io.print(f'Path: {path}')
            await io.print('Type: binary file')
            await io.print(f'Extension: {ext or "(none)"}')
            await io.print(f'Size: {size} bytes')
            return True
    except Exception:
        # If detection fails, fall through and try text read
        pass

    # Text file
    try:
        with open(box, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        await io.error(f'!! describe: cannot read file: {e}')
        return

    lines = content.splitlines()
    words = sum(len(l.split()) for l in lines)
    chars = len(content)

    ext = splitext(path)[1].lower()
    shebang = ''
    if content.startswith('#!'):
        first_nl = content.find('\n')
        shebang = content[:first_nl if first_nl != -1 else None].strip()

    ftype = 'text'
    if ext in ('.py',):
        ftype = 'python source'
    elif ext in ('.md', '.markdown'):
        ftype = 'markdown document'
    elif ext in ('.json',):
        ftype = 'json document'
    elif ext in ('.yml', '.yaml'):
        ftype = 'yaml document'
    elif ext in ('.toml',):
        ftype = 'toml document'
    elif ext in ('.sh',):
        ftype = 'shell script'

    await io.print(f'Path: {path}')
    await io.print('Type: text file')
    await io.print(f'Kind: {ftype}')
    if shebang:
        await io.print(f'Shebang: {shebang}')
    await io.print(f'Counts: {len(lines)} lines, {words} words, {chars} chars')

    # Lightweight content-aware hints
    try:
        if ext == '.json':
            obj = json.loads(content)
            kind = type(obj).__name__
            if isinstance(obj, dict):
                await io.print(f'JSON: object with {len(obj)} keys')
            elif isinstance(obj, list):
                await io.print(f'JSON: array with {len(obj)} items')
            else:
                await io.print(f'JSON: {kind}')
    except Exception:
        pass

    if ext == '.py':
        try:
            mod = ast.parse(content, filename=basename(path))
            doc = ast.get_docstring(mod)
            if doc:
                # Print a single-line summary from the docstring
                first = doc.strip().splitlines()[0]
                await io.print(f'Python: module docstring: {first}')
        except Exception:
            pass

    return True