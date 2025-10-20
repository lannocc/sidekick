import re
import os
import posixpath
from os.path import relpath, exists, isdir

DOCSTRING = """Search for a regular expression PATTERN in each FILE or standard input.

Usage: grep [OPTIONS] PATTERN [FILE...]
       grep --help

Example:
  grep 'hello world' menu.h main.c
  grep '^include' /src/main.c       # Lines starting with 'include'
  grep -r 'config$' /etc            # Files with lines ending in 'config'
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
    process across files, directories,or stdin.
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
        # Options are processed only before the pattern is found.
        if arg.startswith('-') and len(arg) > 1 and pattern is None:
            if arg.startswith('--'):  # Long option
                # This block is for options like --ignore-case
                if arg == '--ignore-case': opts['ignore_case'] = True
                elif arg == '--invert-match': opts['invert_match'] = True
                elif arg == '--line-number': opts['line_number'] = True
                elif arg == '--files-with-matches': opts['files_with_matches'] = True
                elif arg == '--count': opts['count'] = True
                elif arg == '--recursive': opts['recursive'] = True
                else:
                    await io.error(f"!! grep: unknown option: {arg}")
                    return False
            else:  # Short option(s), can be combined (e.g., -inv)
                for flag in arg[1:]:
                    if flag == 'i': opts['ignore_case'] = True
                    elif flag == 'v': opts['invert_match'] = True
                    elif flag == 'n': opts['line_number'] = True
                    elif flag == 'l': opts['files_with_matches'] = True
                    elif flag == 'c': opts['count'] = True
                    elif flag in ('r', 'R'): opts['recursive'] = True
                    else:
                        await io.error(f"!! grep: invalid option -- '{flag}'")
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
    # The 're' module provides full regular expression support, including
    # anchors like ^ (start of line) and $ (end of line), which now work as expected.
    try:
        re_flags = re.IGNORECASE if opts['ignore_case'] else 0
        compiled_pattern = re.compile(pattern, re_flags)
    except re.error as e:
        await io.error(f"!! grep: invalid regular expression '{pattern}': {e}")
        return False

    # --- Search Logic ---
    any_errors = False

    async def search_content(content, virtual_path="", show_filename=False):
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
                    break  # Move to the next file

                if not opts['count']:
                    # Filename prefix is added only when searching multiple files.
                    prefix = f"{virtual_path}:" if virtual_path and show_filename else ""
                    if opts['line_number']:
                        prefix += f"{i + 1}:"
                    await io.print(f"{prefix}{line}")

        if opts['count']:
            prefix = f"{virtual_path}:" if virtual_path and show_filename else ""
            await io.print(f"{prefix}{match_count}")

    async def search_file(virtual_path, show_filename):
        """Wrapper to get file content and call search_content."""
        nonlocal any_errors
        content = await io.os.get(io, virtual_path)
        if content is None:
            # Error was already printed by io.os.get
            any_errors = True
            return
        await search_content(content, virtual_path, show_filename)

    # --- Execution Flow ---
    if not paths:
        if hasattr(io, 'stdin') and io.stdin:
            content = io.stdin.read()
            # No filename prefix for stdin
            await search_content(content)
        else:
            await io.error("!! grep: missing file operand and no piped input")
            return False
    else:
        # First, expand all paths and directories to get a final list of files.
        files_to_search = []
        for p in paths:
            host_p = io.os.box(p, io_context=io)
            if not exists(host_p):
                await io.error(f"!! grep: {p}: No such file or directory")
                any_errors = True
                continue

            if isdir(host_p):
                if not opts['recursive']:
                    await io.error(f"!! grep: {p}: is a directory")
                    any_errors = True
                    continue
                # Recursive search
                base_dir = posixpath.dirname(p) if posixpath.dirname(p) else '.'
                for root, _, files in os.walk(host_p):
                    for name in files:
                        full_host_path = os.path.join(root, name)
                        # Convert host path back to a virtual path relative to the initial dir
                        relative_path = relpath(full_host_path, io.os.box(base_dir, io_context=io))
                        # IMPORTANT: Re-join using POSIX separator for virtual path
                        virtual_file_path = posixpath.normpath(posixpath.join(base_dir, relative_path.replace(os.sep, '/')))
                        files_to_search.append(virtual_file_path)
            else:  # is a file
                files_to_search.append(p)

        # Determine if filenames should be prefixed to output lines.
        # This is standard grep behavior: show names for more than one file.
        show_filenames = len(files_to_search) > 1

        # Now search the collected files
        for f_path in sorted(files_to_search):
            await search_file(f_path, show_filenames)

    return not any_errors

