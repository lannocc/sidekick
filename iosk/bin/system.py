import asyncio
import shlex
import os # Import os for path manipulation

async def iocall(io, argv):
    """Execute a command in the underlying host system.

    Usage: system <command> [args...]
           system --help

    <command>: The command to execute on the host system.
    [args...]: Arguments for the host command.
    --help: Displays this help message.

    Note: This command executes directly on the host OS and may have security implications.
          Use with caution. Arguments that are identified as absolute or relative
          paths (e.g., starting with '/', './', or '../') will be sandboxed
          to the host filesystem's equivalent path. The command will also
          execute in the host equivalent of the user's current working directory.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not argv:
        await io.error('!! system: command required.')
        return False

    # Prepare arguments for the host command, boxing path-like arguments.
    host_argv = []
    for arg in argv:
        # Identify path-like arguments (starting with '/', './', or '../')
        if arg.startswith('/') or arg.startswith('./') or arg.startswith('../'):
            # Box the path-like argument to its host filesystem equivalent
            boxed_arg = io.os.box(arg, io_context=io)
            host_argv.append(boxed_arg)
        else:
            # For non-path-like arguments, pass them as is.
            host_argv.append(arg)

    # Join the arguments to form a single command string suitable for shell execution.
    # shlex.join correctly handles spaces and special characters by quoting them,
    # making it safer to pass to a shell.
    host_command_string = shlex.join(host_argv)

    # Determine the host working directory for the command.
    # The user's current working directory (io.pwd) is a virtual path.
    # It needs to be boxed to its actual location on the host filesystem.
    host_cwd = io.os.box(io.pwd, io_context=io)

    # Ensure the host_cwd exists, otherwise, subprocess might fail or use an unexpected default.
    if not os.path.isdir(host_cwd):
        await io.error(f"!! system: current directory '{io.pwd}' does not exist on host filesystem as '{host_cwd}'. Cannot execute host command.")
        return False

    await io.print(f":: Executing host command: {host_command_string} (in cwd: {host_cwd})")

    try:
        # Create a subprocess to run the host command.
        # Use create_subprocess_shell for simpler execution of command strings,
        # including shell features like pipes or redirection if present in host_command_string.
        # Set the cwd argument to the boxed current working directory.
        process = await asyncio.create_subprocess_shell(
            host_command_string,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=host_cwd # Set the working directory
        )

        # Read stdout and stderr asynchronously.
        stdout_data, stderr_data = await process.communicate()

        # Decode output and print to IOSK's streams.
        # Strip to avoid extra newlines if the host command itself adds them.
        if stdout_data:
            #await io.print(f"\n--- Host STDOUT ---\n{stdout_data.decode().strip()}")
            await io.print(stdout_data.decode())
        if stderr_data:
            #await io.error(f"\n--- Host STDERR ---\n{stderr_data.decode().strip()}")
            await io.error(stderr_data.decode())

        # Wait for the process to finish and get the exit code.
        return_code = await process.wait()

        if return_code == 0:
            await io.print(f":: system command '{argv[0]}' completed successfully.")
            return True
        else:
            await io.error(f"!! system command '{argv[0]}' failed with exit code {return_code}.")
            return False

    except FileNotFoundError:
        # This might occur if the primary command (argv[0]) is not found on the host system.
        await io.error(f"!! system: command not found on host: '{argv[0]}'")
        return False
    except Exception as e:
        # Catch any other exceptions during subprocess creation or communication.
        await io.error(f"!! system: error executing host command: {e}")
        return False

