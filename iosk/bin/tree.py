from sk.util import get_directory_tree_as_text

async def iocall(io, args):
    args = args.split(' ')
    errors = False

    for path in args:
        await io.print(f'{path}:')

        if not await io.os.exists(io, path):
            await io.error('!! tree: path does not exist\n')
            errors = True

        else:
            try: await io.print(get_directory_tree_as_text(io.os.box(path)))
            except Exception as e:
                await io.error('!! tree: failed to traverse path\n')
                errors = True

    return not errors

