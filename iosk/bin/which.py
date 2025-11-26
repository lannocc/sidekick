import os
import posixpath
from os.path import isfile
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

    found_path = None

    # Helper to check if a virtual path is a valid, existing executable file
    async def is_executable_file(virtual_path):
        if not await io.os.exists(io, virtual_path):
            return False
        
        host_path = io.os.box(virtual_path, io_context=io)
        if not isfile(host_path):
            return False
        
        # For .py files, also check if they are valid modules, mimicking the kernel's loader
        if virtual_path.endswith('.py'):
            try:
                mod_base = virtual_path.removesuffix('.py').strip('/').replace('/', '.').replace('-', '_')
                modname_for_spec = f'sk.iosk.{mod_base}'
                spec = importlib.util.spec_from_file_location(modname_for_spec, host_path)
                if not (spec and spec.loader):
                    return False
            except Exception:
                return False
        
        return True

    if '/' in command_name:
        # This is an absolute or relative path, check it directly
        resolved_path = posixpath.normpath(posixpath.join(io.pwd, command_name))
        if await is_executable_file(resolved_path):
            found_path = resolved_path
    else:
        # This is a command name, search the PATH
        path_env = io.environ().get('PATH', '/bin')
        path_dirs = path_env.split(':') if path_env else ['/bin']

        for p_dir in path_dirs:
            if not p_dir: continue

            # Following kernel logic: prioritize .py modules over other executables
            
            # Check for Python module (command_name.py)
            py_path = posixpath.join(p_dir, f"{command_name}.py")
            if await is_executable_file(py_path):
                found_path = py_path
                break
            
            # Check for script/executable (command_name)
            script_path = posixpath.join(p_dir, command_name)
            if await is_executable_file(script_path):
                found_path = script_path
                break
    
    if found_path:
        await io.print(found_path)
        return True
    else:
        await io.error(f"!! which: {command_name} not found in PATH.")
        return False