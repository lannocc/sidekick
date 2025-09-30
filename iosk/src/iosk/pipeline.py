import shlex
import asyncio
import os
from os.path import join, isdir, isfile, exists
import importlib, importlib.util
import sys
import shutil
import traceback
from io import StringIO
from binaryornot.check import is_binary # Used for file checks
from typing import TYPE_CHECKING, List, Tuple, Optional

# Prevent circular imports during runtime for type hints
if TYPE_CHECKING:
    from .kernel import IOSK
    from .io import Context
    from .parser import CommandLineParser

class CommandPipelineExecutor:
    """
    Manages the execution of command pipelines, including alias resolution,
    command lookup, execution of Python modules and scripts, and I/O redirection/pipes.
    """
    def __init__(self, iosk_kernel: 'IOSK'):
        self.os = iosk_kernel # Reference to the IOSK kernel instance

    async def execute_pipeline(self, io: 'Context', raw_command_line: str, parser: 'CommandLineParser') -> bool:
        """
        Interprets arguments, parses for pipes/redirection, and invokes commands.
        This is the main entry point for executing a command line.
        """
        # Step 1: Alias resolution
        first_space_idx = raw_command_line.find(' ')
        cmd_candidate = raw_command_line[:first_space_idx] if first_space_idx != -1 else raw_command_line
        cmd_rest_of_line = raw_command_line[first_space_idx+1:] if first_space_idx != -1 else ''

        alias_resolved_args = raw_command_line
        if cmd_candidate in io.aliases:
            alias_value = io.aliases[cmd_candidate]
            alias_resolved_args = f"{alias_value} {cmd_rest_of_line}".strip()

        # Step 2: Parsing, Substitution, Expansion, and Pipeline construction
        commands, redirect_out_path, redirect_append = await parser.parse_pipeline(io, alias_resolved_args)

        if commands is None: # A parsing error occurred and has been reported by the parser
            return False

        if not commands: # Valid empty command line
            return True

        # Step 3: Differentiate between simple command and full pipeline for optimization
        num_commands = len(commands)
        if num_commands == 1 and not redirect_out_path:
            return await self._execute_single_command(io, commands[0])

        # Step 4: Full Pipeline Execution
        pipe_buffer: Optional[StringIO] = None
        success = True

        for idx, command_argv in enumerate(commands):
            is_last_cmd = (idx == num_commands - 1)

            # Create a forked context for each command in the pipeline.
            # This ensures that each command has its own isolated I/O streams and environment (inherited).
            cmd_io = io.fork()

            # Configure stdin for the current command from the previous command's output
            if pipe_buffer:
                pipe_buffer.seek(0)
                cmd_io.stdin = pipe_buffer
                # Reset pipe_buffer reference for the next iteration (or to prevent accidental reuse)
                pipe_buffer = None

            redirect_file_handle = None
            try:
                # Configure stdout for the current command
                if is_last_cmd and redirect_out_path:
                    mode = 'a' if redirect_append else 'w'
                    host_path = self.os.box(redirect_out_path, io_context=io)
                    parent_dir = os.path.dirname(host_path)

                    # Create parent directories for redirection target if they don't exist
                    if not os.path.exists(parent_dir):
                        try:
                            os.makedirs(parent_dir)
                        except OSError as e:
                            await io.error(f"!! Failed to create directory for redirection target '{parent_dir}': {e}")
                            success = False
                            break # Break pipeline execution

                    redirect_file_handle = open(host_path, mode, encoding='utf-8')
                    cmd_io.stdout = redirect_file_handle
                elif not is_last_cmd:
                    # If not the last command, its output goes to a new pipe_buffer
                    pipe_buffer = StringIO()
                    cmd_io.stdout = pipe_buffer
                else:
                    # For the last command in a pipe without redirection,
                    # it should inherit the original io's stdout (console or other redirect).
                    cmd_io.stdout = io.stdout

                # Execute the single command segment
                success = await self._execute_single_command(cmd_io, command_argv)

            except Exception as e:
                await io.error(f"!! error during pipeline execution: {e}")
                traceback.print_exc()
                success = False
            finally:
                if redirect_file_handle:
                    redirect_file_handle.close()

            if not success:
                break # If any command fails, stop the pipeline

        return success

    async def _execute_single_command(self, io: 'Context', argv: List[str]) -> bool:
        """Resolves and executes a single command with its arguments."""
        if not argv:
            return True # An empty command in a pipeline is a no-op, considered success

        cmd = argv[0]
        cmd_args = argv[1:]

        resolved_internal_path = None
        is_python_module = False
        potential_base_paths = []

        # Determine potential command paths based on virtual path (absolute, relative, or PATH)
        if cmd.startswith('/') or cmd.startswith('./') or cmd.startswith('../'):
            if cmd.startswith('./') or cmd.startswith('../'):
                # Resolve relative to current working directory
                potential_base_paths.append(os.path.normpath(os.path.join(io.pwd if io.pwd else '/', cmd)))
            else:
                # Absolute path
                potential_base_paths.append(cmd)
        else:
            # Search PATH environment variable
            path_env = io.environ().get('PATH', '/bin')
            path_dirs = path_env.split(os.pathsep)
            for p_dir in path_dirs:
                if p_dir: # Skip empty entries
                    potential_base_paths.append(join(p_dir, cmd))

        # Iterate through potential paths to find the first existing and executable one
        # Prioritize Python modules over generic scripts/executables if both exist
        for p_base in potential_base_paths:
            # Check for Python module (.py file with iocall)
            sandboxed_py_path = self.os.box(f'{p_base}.py', io_context=io)
            if exists(sandboxed_py_path) and isfile(sandboxed_py_path):
                # Construct module name for spec from virtual path
                modname_for_spec = f'sk.iosk.{p_base.strip("/").replace("/", ".")}'
                try:
                    spec = importlib.util.spec_from_file_location(modname_for_spec, sandboxed_py_path)
                    if spec and spec.loader: # Ensure it's a loadable Python module
                        resolved_internal_path = p_base
                        is_python_module = True
                        break # Found a Python module, prioritize it and stop searching
                except Exception:
                    pass # Not a loadable Python module or other error, continue search

            # Check for generic script/executable file (without .py extension)
            sandboxed_file_path = self.os.box(p_base, io_context=io)
            if exists(sandboxed_file_path) and isfile(sandboxed_file_path):
                resolved_internal_path = p_base
                is_python_module = False
                break # Found a script, stop search

        if not resolved_internal_path:
            await io.error(f"!! command not found: {cmd}")
            return False

        try:
            if is_python_module:
                modname_for_pymod = resolved_internal_path.strip("/").replace("/", ".")
                # Load the Python module using the kernel's pymod utility
                py_mod = self.os.pymod(modname_for_pymod, self.os.box(f'{resolved_internal_path}.py'))
                if py_mod and hasattr(py_mod, 'iocall'):
                    # Execute the iocall method with the context and arguments
                    result = await py_mod.iocall(io, cmd_args)
                    return result is not False # Commands should return True for success, False for failure
                else:
                    await io.error(f"!! Python module {resolved_internal_path}.py found but missing iocall method.")
                    return False
            else:
                # Execute generic script/executable using the kernel's exec method
                return await self.os.exec(io, resolved_internal_path, cmd_args)
        except Exception as e:
            await io.error(f'!! exception calling {cmd}: {e}')
            traceback.print_exc()
            return False

