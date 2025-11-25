import tiktoken

async def iocall(io, argv):
    """List directory contents recursively in a tree-like format.

    Usage: tree [options] [path ...]
           tree --help

    Options:
      -a        List all entries, including those starting with '.'.
      -c        Count bytes and estimate tokens for the content.
      -d        List directories only.
      -h --help Display this help message.

    [path ...]: The paths to list. If no path is provided use current directory.
    """
    args_list = argv

    count = False
    dirs_only = False
    show_all = False
    paths = []

    for arg in args_list:
        if arg.startswith('-'):
            if arg == '-a':
                show_all = True
            elif arg == '-c':
                count = True
            elif arg == '-d':
                dirs_only = True
            elif arg in ('-h', '--help'):
                await io.print(iocall.__doc__)
                return
            else:
                await io.error(f'!! tree: unknown option: {arg}')
                return
        else:
            paths.append(arg)

    if not paths:
        paths = ['.']

    errors = False

    # Tiktoken setup
    encoding = None
    if count:
        try:
            encoding = tiktoken.get_encoding('cl100k_base')
        except Exception as e:
            await io.error(f"!! tree: could not load tokenizer for -c: {e}")
            # Continue without token counts

    # --- Recursive helper to build and print the tree ---
    async def print_tree_level(virtual_path, prefix=""):
        nonlocal file_count, dir_count
        items = await io.os.list_dir(io, virtual_path, show_all=show_all)
        
        if dirs_only:
            items = [item for item in items if item['type'] == 'dir']

        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            line = f"{prefix}{connector}{item['name']}"

            if item['type'] == 'dir':
                dir_count += 1
                await io.print(line)
                new_prefix = prefix + ("    " if is_last else "│   ")
                await print_tree_level(item['path'], new_prefix)
            else:  # file
                file_count += 1
                if count and item['size'] != -1:
                    size_str = f"({item['size']}b"
                    if encoding:
                        # Avoid reading large binary files for token counting
                        content, is_binary, err = await io.os.get_raw(io, item['path'])
                        if content is not None and not is_binary:
                            try:
                                token_count = len(encoding.encode(content.decode('utf-8')))
                                size_str += f", {token_count}t"
                            except Exception:
                                pass # Ignore decoding errors
                    size_str += ")"
                    line += f" {size_str}"
                await io.print(line)

    # --- Main loop for each path argument ---
    for i, path in enumerate(paths):
        try:
            # Check if the path is a valid directory before starting the tree
            await io.os.list_dir(io, path)
        except (FileNotFoundError, NotADirectoryError):
            await io.error(f'!! tree: path does not exist or is not a directory: {path}')
            errors = True
            if i < len(paths) -1: await io.print("")
            continue

        await io.print(f'{path}{"/" if not path.endswith("/") else ""}:')
        file_count = 0
        dir_count = 0
        
        await print_tree_level(path)

        summary = f"\n{dir_count} director{'y' if dir_count == 1 else 'ies'}"
        if not dirs_only:
            summary += f", {file_count} file{'s' if file_count == 1 else ''}"
        
        await io.print(summary)
        if i < len(paths) -1: await io.print("")

    return not errors