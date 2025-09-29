from sk.util import get_directory_tree_as_text

async def iocall(io, argv):
    """List directory contents recursively in a tree-like format.
    Some files and folders are hidden (this command honors .skignore files).

    Usage: tree [options] [path ...]
           tree --help

    Options:
      -c        Count bytes and estimate tokens for the content.
      -h --help Display this help message.

    [path ...]: The paths to list. If no path is provided use current directory.
    """
    args_list = argv

    count = False
    paths = []

    for arg in args_list:
        if arg.startswith('-'):
            if arg == '-c':
                count = True
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
    for i, path in enumerate(paths):
        await io.print(f'{path}{"/" if not path.endswith("/") else ""}:')

        if not await io.os.exists(io, path):
            await io.error(f'!! tree: path does not exist: {path}\n')
            errors = True
            continue

        try:
            tree_text = get_directory_tree_as_text(io.os.box(path, io_context=io), count=count)
            await io.print(tree_text)
        except Exception as e:
            await io.error(f'!! tree: failed to traverse path for {path}\n')
            errors = True

    return not errors
