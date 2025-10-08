# /bin/replace.py
import os
from typing import List

async def iocall(io, argv: List[str]):
    """
    Replaces occurrences of a string in a file with another string.

    Usage: replace <filename> <old_string> <new_string>

    <filename>: The path to the file to modify.
    <old_string>: The string to search for.
    <new_string>: The string to replace with.
    """
    if len(argv) != 3:
        await io.error("!! Usage: replace <filename> <old_string> <new_string>")
        return False

    file_path = argv[0]
    old_string = argv[1]
    new_string = argv[2]

    host_path = io.os.box(file_path, io_context=io)

    if not os.path.exists(host_path):
        await io.error(f"!! File not found: {file_path}")
        return False
    if not os.path.isfile(host_path):
        await io.error(f"!! Not a file: {file_path}")
        return False

    try:
        # Read the original content
        with open(host_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Perform the replacement
        new_content = content.replace(old_string, new_string)

        # Write the modified content back to the file
        with open(host_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        await io.print(f":: Replaced '{old_string}' with '{new_string}' in '{file_path}'.")
        return True
    except Exception as e:
        await io.error(f"!! Error replacing string in '{file_path}': {e}")
        return False

