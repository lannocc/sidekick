import os
from os.path import join, isfile, exists, normpath
import importlib, importlib.util

SHELL_BUILTINS = ['exit', 'logout']

async def iocall(io, argv):
    """Locate a command executable in the PATH.

    Usage: which <command>
           which --help

    <command>: The name of the command to locate.
    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not argv:
        await io.error("!! which: command argument required.")
        return False
    if len(argv) > 1:
        await io.error("!! which: too many arguments. Usage: which <command>")
        return False

    command_name = argv[0]

    # First, check if the command is a shell built-in
    if command_name in SHELL_BUILTINS:
        await io.print(f"{command_name}: shell built-in command")
        return True

    # List of potential virtual paths where the command might be found.
    # We follow IOSK.call's logic for prioritization: .py files first, then scripts.
    candidate_virtual_paths = []

    # Case 1: Command is an absolute or explicit relative path (e.g., /bin/ls, ./script.sh)
    # For these, we only check the given path itself, not with .py extensions implicitly.
    if command_name.startswith('/') or command_name.startswith('./') or command_name.startswith('../'):
        candidate_virtual_paths.append(normpath(command_name))
    else:
        # Case 2: Command is a bare name, search PATH or default to /bin
        path_env = io.environ().get('PATH')
        path_dirs = path_env.split(os.pathsep) if path_env else []
        if not path_dirs:
            # Default to /bin if PATH is not set or empty
            path_dirs = ['/bin']

        for p_dir in path_dirs:
            if not p_dir: # Skip empty entries in PATH
                continue

            # IOSK's kernel.call prioritizes .py files that are valid Python modules.
            # Then it checks for plain executable files.
            # We construct candidate paths in this priority order.

            # Candidate 1: Check for command_name.py (and if it's a loadable Python module)
            virtual_py_path = normpath(join(p_dir, f'{command_name}.py'))
            host_py_path = io.os.box(virtual_py_path, io_context=io)
            if exists(host_py_path) and isfile(host_py_path):
                # Simulate spec creation to ensure it's a valid Python module,
                # as kernel.call would do.
                modname_for_spec = f'sk.iosk.{virtual_py_path.strip("/").replace("/", ".")}'
                try:
                    spec = importlib.util.spec_from_file_location(modname_for_spec, host_py_path)
                    if spec and spec.loader:
                        candidate_virtual_paths.append(virtual_py_path)
                except Exception:
                    pass # Not a loadable Python module, ignore for this check

            # Candidate 2: Check for command_name (plain executable)
            virtual_cmd_path = normpath(join(p_dir, command_name))
            host_cmd_path = io.os.box(virtual_cmd_path, io_context=io)
            if exists(host_cmd_path) and isfile(host_cmd_path):
                candidate_virtual_paths.append(virtual_cmd_path)

    found_virtual_path = None
    for virtual_path in candidate_virtual_paths:
        # The candidate_virtual_paths list is already ordered by priority,
        # so the first one we find that actually exists and is a file is the one.
        # (The existence and isfile checks are already implicitly done in the loop above
        # for bare names, but explicitly confirm for absolute paths and as a final check)
        host_path = io.os.box(virtual_path, io_context=io)
        if exists(host_path) and isfile(host_path):
            found_virtual_path = virtual_path
            break # Found the first matching executable

    if found_virtual_path:
        await io.print(found_virtual_path)
        return True
    else:
        await io.error(f"!! which: {command_name} not found in PATH.")
        return False

