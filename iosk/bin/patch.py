#!/usr/bin/env python

import re

# iocall is the entry point for IOSK commands that are .py files.
async def iocall(io, args):
    #if '--help' in args:
    if args == '--help':
        await io.print("Usage: patch <targetfile> <patchfile>")
        await io.print("Applies a diff to a file.")
        await io.print("Note: This initial version can apply simple line-based patches.")
        return
        
    args = args.split(' ')

    if len(args) != 2:
        await io.error("Usage: patch <targetfile> <patchfile>")
        return

    target_file_path = args[0]
    patch_path = args[1]

    # 1. Read the patch content
    try:
        patch_content = await io.os.get(io, patch_path)
    except FileNotFoundError:
        await io.error(f"Error: Patch file not found at {patch_path}")
        return

    '''
    # 2. Extract the target file path from the patch headers
    target_file_path = None
    original_file_header_pattern = re.compile(r'--- (.*)')
    new_file_header_pattern = re.compile(r'\+\+\+ (.*)')

    for line in patch_content.splitlines():
        # Look for the '---' header to get the original file path
        match_orig = original_file_header_pattern.match(line)
        if match_orig:
            target_file_path = match_orig.group(1)
            # Assuming the '+++' header refers to the same file for a simple patch
            break
        
    if not target_file_path:
        await io.error("Error: Could not determine target file path from patch headers.")
        return
    '''
    

    # 3. Read the content of the original file from the IOSK filesystem
    try:
        # keepends=False so we don't have to deal with '\n' during patching
        original_content = await io.os.get(io, target_file_path)
        original_lines = original_content.splitlines(keepends=False) 
    except FileNotFoundError:
        await io.error(f"Error: Original file not found at {target_file_path}")
        return

    # --- Start Generic Simple Patching Logic ---
    new_lines = []
    diff_lines = patch_content.splitlines(keepends=False)
    
    # Track current line in original_lines
    original_idx = 0
    in_hunk = False

    for line in diff_lines:
        if line.startswith('---') or line.startswith('+++'):
            continue # Headers already processed or irrelevant now
        
        if line.startswith('@@'):
            # Hunk header: @@ -start,count +start,count @@
            match = re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                original_hunk_start_line = int(match.group(1)) - 1 # 0-indexed
                # Add context lines from original file before the hunk starts
                while original_idx < original_hunk_start_line:
                    new_lines.append(original_lines[original_idx])
                    original_idx += 1
                in_hunk = True
            else:
                await io.error(f"Error: Malformed hunk header: {line}")
                return
            continue

        if not in_hunk:
            # If there are lines before the first hunk, they are treated as context.
            # Append them as is if we encounter them.
            new_lines.append(line)
            continue
        
        if line.startswith('-'):
            # This line is removed from the original. Advance original_idx.
            if original_idx >= len(original_lines) or original_lines[original_idx] != line[1:]:
                await io.error(f"Error: Mismatch in removed line at original_idx {original_idx}.")
                return
            original_idx += 1
        elif line.startswith('+'):
            # This line is added. Append it to new_lines.
            new_lines.append(line[1:])
        elif line.startswith(' '):
            # This is a context line. Append it to new_lines and advance original_idx.
            if original_idx >= len(original_lines) or original_lines[original_idx] != line[1:]:
                await io.error(f"Error: Mismatch in context line at original_idx {original_idx}.")
                return
            new_lines.append(line[1:])
            original_idx += 1
        else:
            # Unknown line type in hunk.
            await io.error(f"Error: Unknown diff line type in hunk: {line}")
            return
            
    # Append any remaining lines from the original file that were not part of any diff hunk
    while original_idx < len(original_lines):
        new_lines.append(original_lines[original_idx])
        original_idx += 1

    # --- End Generic Simple Patching Logic ---

    final_content = "\n".join(new_lines)
    # Re-add a trailing newline if the original file had one (common for text files)
    if original_content.endswith('\n') and not final_content.endswith('\n'):
        final_content += '\n'

    #await io.print(f"Patched content for '{target_file_path}' has been generated:")
    #await io.print(f"```skrip\n{final_content}\n```")
    #await io.print(f"Please use 'mv' to replace the original file with the auto-saved output from this markdown block.")
    
    with open(io.os.box(target_file_path), 'w') as f:
        f.write(final_content)
        
    await io.print(f':: file successfully patched: {target_file_path}')
