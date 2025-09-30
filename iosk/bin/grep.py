import re
import os
from os.path import join, relpath, normpath

DOCSTRING = """Search for PATTERN in each FILE or standard input.

Usage: grep [OPTIONS] PATTERN [FILE...]
       grep --help

Example:
  grep 'hello world' menu.h main.c
  grep -r 'include' /src
  ls /bin | grep .py

Options:
  -i, --ignore-case    Ignore case distinctions in PATTERN.
  -v, --invert-match   Invert the sense of matching, to select non-matching lines.
  -n, --line-number    Prefix each line of output with the 1-based line number
                       within its input file.
  -l, --files-with-matches
                       Suppress normal output; instead print the name of each
                       input file from which output would normally have been
                       printed.
  -c, --count          Suppress normal output; instead print a count of matching
                       lines for each input file.
  -r, -R, --recursive  Read all files under each directory, recursively.
  --help               Display this help message and exit.
"""

async def iocall(io, argv):
    """
    Handle the 'grep' command execution.
    This function parses arguments, compiles the regex, and manages the search
    process across files, directories, or stdin.
    """
    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    # --- Argument Parsing ---
    opts = {
        'ignore_case': False,
        'invert_match': False,
        'line_number': False,
        'files_with_matches': False,
        'count': False,
        'recursive': False
    }
    pattern = None
    paths = []

    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith('-') and pattern is None:
            if arg in ('-i', '--ignore-case'):
                opts['ignore_case'] = True
            elif arg in ('-v', '--invert-match'):
                opts['invert_match'] = True
            elif arg in ('-n', '--line-number'):
                opts['line_number'] = True
            elif arg in ('-l', '--files-with-matches'):
                opts['files_with_matches'] = True
            elif arg in ('-c', '--count'):
                opts['count'] = True
            elif arg in ('-r', '-R', '--recursive'):
                opts['recursive'] = True
            else:
                await io.error(f"!! grep: unknown option: {arg}")
                return False
        elif pattern is None:
            pattern = arg
        else:
            paths.append(arg)
        i += 1

    if pattern is None:
        await io.error("!! grep: pattern required")
        await io.print("Usage: grep [OPTIONS] PATTERN [FILE...]")
        return False

    # --- Regex Compilation ---
    try:
        re_flags = re.IGNORECASE if opts['ignore_case'] else 0
        compiled_pattern = re.compile(pattern, re_flags)
    except re.error as e:
        await io.error(f"!! grep: invalid regular expression '{pattern}': {e}")
        return False

    # --- Search Logic ---
    any_errors = False
    
    async def search_content(content, virtual_path=""):
        """Searches content string, prints matches based on options."""
        nonlocal any_errors
        match_count = 0
        file_printed = False

        lines = content.splitlines()
        for i, line in enumerate(lines):
            match = compiled_pattern.search(line)
            is_match = bool(match)
            
            # Invert match if -v is used
            if opts['invert_match']:
                is_match = not is_match

            if is_match:
                match_count += 1
                if opts['files_with_matches']:
                    if not file_printed:
                        await io.print(virtual_path)
                        file_printed = True
                    break # Move to next file
                
                if not opts['count']:
                    prefix = f"{virtual_path}:" if virtual_path else ""
                    if opts['line_number']:
                        prefix += f"{i + 1}:"
                    await io.print(f"{prefix}{line}")

        if opts['count']:
            prefix = f"{virtual_path}:" if virtual_path else ""
            await io.print(f"{prefix}{match_count}")

    async def search_file(virtual_path):
        """Wrapper to get file content and call search_content."""
        nonlocal any_errors
        content = await io.os.get(io, virtual_path)
        if content is None:
            # Error was already printed by io.os.get
            any_errors = True
            return
        await search_content(content, virtual_path)


    # --- Execution Flow ---
    if not paths:
        if hasattr(io, 'stdin') and io.stdin:
            content = io.stdin.read()
            await search_content(content)
        else:
            await io.error("!! grep: missing file operand and no piped input")
            return False
    else:
        # Expand paths, handling recursion
        files_to_search = []
        for p in paths:
            host_p = io.os.box(p, io_context=io)
            if not os.path.exists(host_p):
                await io.error(f"!! grep: {p}: No such file or directory")
                any_errors = True
                continue
            
            if os.path.isdir(host_p):
                if not opts['recursive']:
                    await io.error(f"!! grep: {p}: is a directory")
                    any_errors = True
                    continue
                # Recursive search
                for root, _, files in os.walk(host_p):
                    for name in files:
                        full_host_path = join(root, name)
                        # Convert host path back to a virtual path for display
                        relative_host_path = relpath(full_host_path, host_p)
                        virtual_file_path = normpath(join(p, relative_host_path))
                        files_to_search.append(virtual_file_path)
            else: # is a file
                files_to_search.append(p)
        
        # Now search the collected files
        for f_path in files_to_search:
            await search_file(f_path)
            
    return not any_errors
