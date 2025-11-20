import os
import posixpath

async def iocall(io, argv):
    """Change the current working directory.

    Usage: cd [directory]
           cd --help

    [directory]: The path to the directory to change to.
                 If no directory is specified, it changes to the user's home directory (/home/<user>).
    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    target_path_input = None

    if not argv:
        # No arguments, change to user's home directory
        target_path_input = f'/home/{io.session.user}'
    elif len(argv) == 1:
        target_path_input = argv[0]
    else:
        # More than one argument is an error for 'cd'
        await io.error('!! cd: too many arguments. Usage: cd [directory]')
        return False

    # Resolve the target path to an absolute virtual path
    if target_path_input.startswith('/'):
        canonical_virtual_path = posixpath.normpath(target_path_input)
    else:
        canonical_virtual_path = posixpath.normpath(posixpath.join(io.pwd, target_path_input))

    # Ensure it's truly an absolute path in the virtual FS (e.g., handles '//' or 'a/../b')
    if not canonical_virtual_path.startswith('/'):
        # This case should ideally not happen if paths are correctly normalized and start with '/'
        canonical_virtual_path = '/' + canonical_virtual_path

    # Check if this virtual path exists as a directory on the host filesystem
    host_path = io.os.box(canonical_virtual_path)

    if not os.path.exists(host_path):
        await io.error(f"!! cd: no such file or directory: {target_path_input}")
        return False
    if not os.path.isdir(host_path):
        await io.error(f"!! cd: not a directory: {target_path_input}")
        return False

    io.pwd = canonical_virtual_path
    await io.print(f":: current directory changed to: {io.pwd}")
    return True

