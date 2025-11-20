# sk/iosk/proc.py
# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import traceback
import posixpath
import importlib.util
from os.path import exists, isfile
from io import StringIO
import sys

from .io import Context

class Process:
    """A lightweight wrapper to represent a single, ongoing command execution."""
    def __init__(self, pid, user, command, start_time, task):
        self.pid = pid
        self.user = user
        self.command_str = ' '.join(command) # Store the command as a string
        self.start_time = start_time
        self.task = task

class ProcessManager:
    """Manages process creation, execution, and tracking for the IOSK kernel."""
    def __init__(self, kernel):
        self.os = kernel
        self.process_table = {}
        self.next_pid = 1
    
    async def call(self, io:Context, command_to_execute:str, original_line_for_history:str=None):
        """Interpret arguments, parse for pipes/redirection, and invoke commands."""
        # If original_line_for_history is not provided, it's a non-interactive call.
        # Use the command itself for the history line; it will be filtered by `io.base` anyway.
        history_line = original_line_for_history if original_line_for_history is not None else command_to_execute
        # Delegate the entire pipeline execution to the CommandPipelineExecutor
        return await self.os.pipeline_executor.execute_pipeline(io, command_to_execute, history_line, self.os.parser)

    async def execute_transient_command(self, base_io: Context, command_str: str, pwd: str) -> str:
        """
        Executes a command in a temporary, non-interactive context and captures its output.
        Used for features like 'watch'.
        """
        if not await self.os.fs.exists(base_io, pwd):
            return f"watch error: directory not found: {pwd}"
            
        temp_io = base_io.fork()
        temp_io.base = False  # Mark as a non-base, transient session
        temp_io.dev = '/dev/null' # Does not have a real device
        temp_io.pwd = pwd

        # Redirect stdout and stderr to a string buffer
        output_capture = StringIO()
        temp_io.stdout = output_capture
        temp_io.stderr = output_capture

        try:
            # Execute the command pipeline
            await self.call(temp_io, command_str)
        except Exception as e:
            # Capture exceptions during command parsing/execution as well
            traceback.print_exc(file=output_capture)

        return output_capture.getvalue()

    async def exec(self, io:Context, path:str, argv:list=None):
        """When you know what you need and you've come prepared (arguments).
        This method expects `path` to be an absolute path within the sandboxed
        filesystem (e.g., /bin/myscript). It does not search the PATH environment
        variable for the executable itself."""
        if argv is None:
            argv = []

        file = self.os.fs.box(path) # path is expected to be an absolute virtual path from `call`
        if not exists(file):
            await io.error(f'!! exec path not found: {path}')
            return False # Indicate failure

        with open(file, 'r') as file:
            shebang = file.readline().rstrip()

        if shebang and shebang.startswith('#!'):
            shebang = shebang[2:]

            if shebang.startswith('/bin/'): # HACK
                interpreter = shebang[5:] # e.g., 'skrip'
                script_and_args_for_interpreter = [path] + argv

                # --- BEGIN FIX ---
                # The original code called `self.call`, creating a potential infinite recursion
                # if a script specified itself as its interpreter. The fix is to directly
                # resolve the interpreter as a Python module and execute its `iocall` method,
                # bypassing the main `call` pathway. This breaks the recursive loop.

                # We resolve the interpreter path and check if it's a valid Python module.
                # This logic is a simplified version of what's in `pipeline.py`.
                interpreter_path = posixpath.join('/bin', interpreter)
                sandboxed_py_path = self.os.fs.box(f'{interpreter_path}.py', io_context=io)

                if exists(sandboxed_py_path) and isfile(sandboxed_py_path):
                    try:
                        modname_for_pymod = interpreter_path.strip("/").replace("/", ".").replace("-", "_")
                        py_mod = self.os.pymod(modname_for_pymod, sandboxed_py_path)
                        if py_mod and hasattr(py_mod, 'iocall'):
                            # Execute the interpreter's iocall method directly.
                            return await py_mod.iocall(io, script_and_args_for_interpreter)
                        else:
                            await io.error(f"!! interpreter '{interpreter}' is not a valid module with iocall.")
                            return False
                    except Exception as e:
                        await io.error(f"!! exception calling interpreter '{interpreter}': {e}")
                        traceback.print_exc()
                        return False
                else:
                    await io.error(f"!! interpreter not found or not a Python module: {interpreter_path}.py")
                    return False
                # --- END FIX ---

            else:
                await io.error(f'!! bad shebang: {path}')
                return False # Indicate failure

        else:
            await io.error(f'!! no shebang: {path}')
            # TODO support real binaries (executables), etc.
            return False # Indicate failure