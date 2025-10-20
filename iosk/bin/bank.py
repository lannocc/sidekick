import os
import uuid
import posixpath

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
        If a given path is not found and it does not already end with .md,
        the command will also try to find the file by appending a .md extension.

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

            # Use the staging mechanism to capture the raw piped content
            io.stage_bank(bank_key)
            try:
                # "print" the content, which gets captured by the banking stage.
                # Unlike file-based banking, we don't execute piped content, just capture it.
                await io.print(content)
            finally:
                # This call finalizes the capture, moving the content into io.banks
                io.stage_normal()

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
        resolved_path = posixpath.normpath(path_arg)
    elif path_arg.startswith('./') or path_arg.startswith('../'):
        resolved_path = posixpath.normpath(posixpath.join(io.pwd, path_arg))
    else:
        resolved_path = posixpath.normpath(posixpath.join('/bank', path_arg))

    # Try adding .md if the original path is not found and doesn't already end with .md
    if not await io.os.exists(io, resolved_path) and not resolved_path.endswith('.md'):
        path_with_md = resolved_path + '.md'
        if await io.os.exists(io, path_with_md):
            resolved_path = path_with_md

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

