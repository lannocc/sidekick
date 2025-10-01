import os
import uuid

async def iocall(io, argv):
    """Load a file's content into core memory banks.

    Usage: bank <path components...>
           ... | bank
           bank --help

    Loads the content of a file into the user's memory banks.
    If the file has a shebang (e.g., #!/bin/skrip), it is executed and
    its output is captured. Otherwise, the raw file content is loaded directly.

    <path components...>: The path to the file to load. If multiple arguments
        are given, they are joined with '/' to form the final path.
        - If absolute (e.g., /etc/skrc), it's used directly.
        - If relative (e.g., ./myskrip), it's resolved from the current directory.
        - Otherwise (e.g., role devops), it's treated as a path under /bank
          (becoming /bank/role/devops).

    If no path is given and input is piped from stdin, the piped content
    is loaded directly into memory without being executed as a skrip.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    # Case 1: Piped input from stdin
    if not argv and hasattr(io, 'stdin') and io.stdin:
        content = io.stdin.read().strip()
        if content:
            # For piped content, we don't execute, just store.
            # Use a unique key to avoid collisions.
            bank_key = f"stdin-bank-{uuid.uuid4().hex[:8]}"
            io.banks[bank_key] = content
            await io.print(f":: content piped into memory bank '{bank_key}'")
        return True

    # Case 2: File path argument(s)
    if not argv:
        await io.error("!! bank: requires a path argument, or piped input.")
        return False

    path_arg = "/".join(argv)
    resolved_path = ""

    # Resolve path
    if path_arg.startswith('/'):
        resolved_path = os.path.normpath(path_arg)
    elif path_arg.startswith('./') or path_arg.startswith('../'):
        resolved_path = os.path.normpath(os.path.join(io.pwd, path_arg))
    else:
        resolved_path = os.path.normpath(os.path.join('/bank', path_arg))

    # Get the file content first. io.os.get handles errors like not found.
    content = await io.os.get(io, resolved_path)
    if content is None:
        # io.os.get already printed an error
        return False

    # Check for shebang
    if content.strip().startswith('#!'):
        # --- HAS SHEBANG: Execute the skrip and capture its output ---
        io.stage_bank(resolved_path)
        try:
            await io.os.exec(io, resolved_path, [])
        except Exception as e:
            io.stage_normal()
            await io.error(f'!! bank: error executing skrip {resolved_path}: {e}')
            return False
        finally:
            io.stage_normal() # This stores the captured output in io.banks

        await io.print(f":: memory bank loaded from '{resolved_path}' (executed)")
    else:
        # --- NO SHEBANG: Load the raw content directly ---
        io.banks[resolved_path] = content
        await io.print(f":: memory bank loaded from '{resolved_path}' (raw content)")

    return True

