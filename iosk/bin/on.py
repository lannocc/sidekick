import shlex
import asyncio
from typing import List

DOCSTRING = """Execute a command on a remote, connected host.

Usage: on <host> <command...>
       on --help

<host>: The hostname of a connected peer system in the network mesh.
<command...>: The command and its arguments to execute on the remote host.

The command's output is streamed back and displayed locally.
"""

async def iocall(io, argv: List[str]):
    """Handle the 'on' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    # Check for the kernel's port manager subsystem.
    if not hasattr(io.os, 'port') or not io.os.port:
        await io.error("!! on: network subsystem is not available.")
        return False

    # Validate arguments: must have at least <host> and <command>.
    if len(argv) < 2:
        await io.error("!! on: requires at least 2 arguments: <host> <command...>")
        await io.print("Usage: on <host> <command...>")
        return False

    host = argv[0]
    command_args = argv[1:]
    command_str = shlex.join(command_args)

    port_manager = io.os.port

    # Validate that the host is a known, connected peer.
    if host not in port_manager.peers:
        await io.error(f"!! on: host '{host}' is not a connected peer.")
        if not port_manager.peers:
            await io.print(":: No peers are currently connected. Use 'mesh <host>' to connect.")
        else:
            await io.print(f":: Connected peers: {', '.join(port_manager.peers.keys())}")
        return False

    # Print the execution header, as shown in the proposal's example.
    await io.print(f":: on {host}:")

    # This command relies on a high-level method on the PortManager to handle
    # the request/response streaming logic for remote execution. This method
    # is a necessary part of the Netroom architecture for this command to function.
    # It is assumed to be named `stream_remote_exec` and to handle the full RPC
    # lifecycle, printing streamed output directly to the provided `io` context.

    try:
        # The `stream_remote_exec` method is expected to handle the full lifecycle
        # of the remote command and stream its output.
        success = await port_manager.stream_remote_exec(host, command_str, io)
        return success
    except AttributeError:
        # This catch is a safeguard for development if the method doesn't exist yet.
        await io.error("!! on: command failed. The `stream_remote_exec` method is not implemented in the PortManager.")
        return False
    except Exception as e:
        await io.error(f"!! on: an unexpected error occurred during remote execution: {e}")
        return False
