import posixpath

async def iocall(io, argv):
    """Clear a memory bank.

    Usage: clbank <path components...>
           clbank -h | --help

    Removes a named memory bank from the user's session.
    The path resolution is identical to the 'bank' command.

    <path components...>: The path/key of the bank to clear.
        - If absolute (e.g., /path/to/file), it's used directly.
        - If relative (e.g., ./file), it's resolved from the current directory.
        - Otherwise (e.g., role devops), it's treated as a path under /bank
          (becoming /bank/role/devops).
    """
    if '-h' in argv or '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not argv:
        await io.error("!! clbank: requires a path argument.")
        await io.print("Usage: clbank <path components...>")
        return False

    # Path resolution logic, adapted from bin/bank.py
    path_arg = "/".join(argv)
    resolved_path = ""

    if path_arg.startswith('/'):
        resolved_path = posixpath.normpath(path_arg)
    elif path_arg.startswith('./') or path_arg.startswith('../'):
        resolved_path = posixpath.normpath(posixpath.join(io.pwd, path_arg))
    else:
        resolved_path = posixpath.normpath(posixpath.join('/bank', path_arg))

    # To maintain symmetry with `bank`, which might add `.md` to the path
    # before using it as a key, we check for both versions.
    bank_key_to_clear = None
    if resolved_path in io.session.banks:
        bank_key_to_clear = resolved_path
    elif not resolved_path.endswith('.md'):
        path_with_md = resolved_path + '.md'
        if path_with_md in io.session.banks:
            bank_key_to_clear = path_with_md

    if bank_key_to_clear:
        del io.session.banks[bank_key_to_clear]
        await io.print(f":: cleared memory bank '{bank_key_to_clear}'")
        return True
    else:
        await io.error(f"!! clbank: memory bank not found: '{resolved_path}'")
        return False