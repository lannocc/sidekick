# sk/worker.py

import re
import os
import subprocess
import tempfile
import shutil

# Regex to find code blocks. This version captures the entire info
# string line after the backticks (e.g., "python:path/to/file.py").
CODEBLOCK_REGEX = re.compile(r'```(?P<language>[^\n]*)\n(?P<code>.*?)\n```', re.DOTALL)

# Regex to find ">>> BEGIN ... <path>:" markers before code blocks (e.g., BEGIN FILE, BEGIN NEW FILE, BEGIN PATCH).
BEGIN_FILE_REGEX = re.compile(r'>>> BEGIN .*\s+([^:\n]+):')

# Regex to find file paths in backticks, updated to allow spaces in the path.
FILENAME_REGEX = re.compile(r'`([^`]+)`')

# Regex to find a filename inside a markdown heading.
HEADING_FILENAME_REGEX = re.compile(r'^#+\s*.*`([^`\n]+)`.*$', re.MULTILINE)

# Regex to find a filename on a line ending with `filename`:
# e.g., "The content for `path/to/file.py`:"
LINE_ENDING_IN_FILENAME_REGEX = re.compile(r'.*`([^`\n]+)`:\s*$', re.MULTILINE | re.IGNORECASE)


def extract_target_from_diff(diff_content):
    """Extracts the target filename from a diff's '---' or '+++' line."""
    # Prioritize the '+++' line as it usually indicates the new file path.
    match = re.search(r'^\+\+\+ (?:b/)?([^\t\n]+)', diff_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Fallback to the '---' line.
    match = re.search(r'^--- (?:a/)?([^\t\n]+)', diff_content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_target_from_code(code_content):
    """
    Extracts a filename from comments in the first few lines of a code block.
    This is a fallback mechanism.
    """
    lines = code_content.split('\n', 5) # Check up to the first 5 lines
    for line in lines:
        line = line.strip()
        # Look for patterns like "# file: /path/to/file.py" or "// /path/to/file.js"
        # Handles various comment styles and an optional "file:" prefix.
        match = re.search(r'^(?:#|//|--|<!--|\*)\s*(?:file:\s*)?([\w./\-\\]+)', line, re.IGNORECASE)
        if match:
            path = match.group(1)
            # A simple heuristic to avoid matching non-path comments like "# TODO" or common code.
            # It must contain a separator or a dot.
            if '.' in path or '/' in path or '\\' in path:
                 # Avoid matching version numbers or other irrelevant dotted numbers at line start
                 if re.match(r'^\d+\.\d+', path):
                     continue
                 return path.strip()
    return None


def is_plausible_filename(candidate: str) -> bool:
    """
    Determines if a candidate string is a plausible filename.
    Rejects common placeholders and requires some structural characteristics.
    """
    candidate = candidate.strip()
    if not candidate or candidate in ('...', '....', '…'):
        return False

    # A plausible filename has a path separator, an extension, or is a single word
    # (like Makefile, Dockerfile) without spaces. This helps avoid capturing
    # random backticked words that aren't filenames.
    return (
        '/' in candidate or
        '\\' in candidate or
        '.' in candidate or
        ' ' not in candidate
    )


def apply_patch(target_file, diff_content):
    """Applies a diff to a target file using the system's patch command."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".diff", encoding='utf-8') as diff_file:
            diff_file.write(diff_content)
            diff_filename = diff_file.name

        # Ensure the target directory exists before attempting to patch.
        target_dir = os.path.dirname(target_file)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)

        # If the target file doesn't exist, create it so `patch` can operate on it.
        if not os.path.exists(target_file):
            with open(target_file, 'w', encoding='utf-8') as f:
                pass # Create an empty file.

        # Execute the system's `patch` command with a fuzz factor of 3.
        result = subprocess.run(
            ['patch', '-F', '3', target_file, diff_filename],
            capture_output=True, text=True, check=False
        )

        os.unlink(diff_filename)

        if result.returncode == 0:
            return True, f"Successfully patched {target_file}"
        else:
            # Provide detailed error message from patch command if it fails.
            return False, f"Error patching {target_file}:\n{result.stderr or result.stdout}"

    except FileNotFoundError:
        return False, "Error: the 'patch' command was not found. Is it installed and in your PATH?"
    except Exception as e:
        return False, f"An exception occurred while applying patch to {target_file}: {e}"


def do_work_on_block(language_info, code_content, context_before_block, transcript_path):
    """
    Processes a single code block, applies changes, and returns a summary.
    Also appends a summary of the action to the transcript.
    """
    filename = None
    lang = language_info.split(':', 1)[0].lower().strip()

    if ':' in language_info:
        parts = language_info.split(':', 1)
        candidate = parts[1].strip()
        if is_plausible_filename(candidate):
            filename = candidate

    search_window = context_before_block[-512:]

    if not filename:
        begin_file_matches = BEGIN_FILE_REGEX.findall(search_window)
        if begin_file_matches:
            candidate = begin_file_matches[-1].strip()
            if candidate: filename = candidate

    if not filename:
        heading_matches = HEADING_FILENAME_REGEX.findall(search_window)
        if heading_matches:
            candidate = heading_matches[-1].strip()
            if is_plausible_filename(candidate): filename = candidate

    if not filename:
        line_ending_matches = LINE_ENDING_IN_FILENAME_REGEX.findall(search_window)
        if line_ending_matches:
            candidate = line_ending_matches[-1].strip()
            if is_plausible_filename(candidate): filename = candidate

    if not filename:
        context_filenames = FILENAME_REGEX.findall(search_window)
        if context_filenames:
            for candidate in reversed(context_filenames):
                if is_plausible_filename(candidate.strip()):
                    filename = candidate.strip()
                    break

    if not filename:
        filename = extract_target_from_code(code_content)

    summary_line = ""

    if lang in ('diff', 'patch'):
        target_file = extract_target_from_diff(code_content) or filename
        if not target_file:
            summary_line = f"SKIPPED: Could not determine target file for a diff block."
        else:
            backup_info = ""
            if os.path.exists(target_file):
                backup_filename = f"{target_file}.bak"
                try:
                    shutil.copy2(target_file, backup_filename)
                    backup_info = f" (original saved to {backup_filename})"
                except Exception as e:
                    summary_line = f"FAILED TO BACK UP: {target_file}\n   {e}"

            if not summary_line:
                success, message = apply_patch(target_file, code_content)
                if success:
                    summary_line = f"PATCHED: {target_file}{backup_info}"
                else:
                    summary_line = f"FAILED TO PATCH: {target_file}\n   {message}"
    else:
        target_file = filename
        if not target_file:
            display_lang = language_info or 'unspecified'
            summary_line = f"SKIPPED: Could not determine filename for a '{display_lang}' code block."
        else:
            try:
                directory = os.path.dirname(target_file)
                if directory:
                    os.makedirs(directory, exist_ok=True)

                backup_info = ""
                if os.path.exists(target_file):
                    backup_filename = f"{target_file}.bak"
                    try:
                        shutil.copy2(target_file, backup_filename)
                        backup_info = f" (original saved to {backup_filename})"
                    except Exception as e:
                        summary_line = f"FAILED TO BACK UP: {target_file}\n   {e}"

                if not summary_line:
                    with open(target_file, 'w', encoding='utf-8') as f:
                        f.write(code_content)
                    summary_line = f"WROTE: {target_file}{backup_info}"

            except Exception as e:
                summary_line = f"FAILED TO WRITE: {target_file}\n   {e}"

    if summary_line and transcript_path:
        summary_to_log = f"--- WORK ACTION ---\n{summary_line}\n"
        try:
            with open(transcript_path, 'a', encoding='utf-8') as f:
                f.write("\n")
                f.write(summary_to_log)
        except Exception:
            pass

    return summary_line


def do_work(prompt, answer, transcript_path):
    """
    Processes an AI's answer to extract code, apply changes to the filesystem,
    and generate a summary of the work performed.

    Returns a tuple of (modified_answer_for_display, summary_of_work).
    """
    summary_lines = []
    processed_answer = answer

    matches = list(CODEBLOCK_REGEX.finditer(answer))
    # Iterate in reverse to avoid messing up string indices during replacement.
    for match in reversed(matches):
        language_info = match.group('language').strip()
        code = match.group('code')
        original_block = match.group(0)

        # --- Filename Inference Logic ---
        filename = None
        # Default lang is the part before ':', or the whole string if no ':'.
        lang = language_info.split(':', 1)[0].lower().strip()

        # 1. Prioritize filename from the language info line (e.g., ```python:path/to/file.py)
        # This is considered the strongest signal for the filename.
        if ':' in language_info:
            parts = language_info.split(':', 1)
            candidate = parts[1].strip()
            if is_plausible_filename(candidate):
                filename = candidate

        # --- Fallback to existing methods if filename not found in language line ---
        search_window = answer[max(0, match.start() - 512):match.start()]

        # 2. Look for ">>> BEGIN ... <path>:" marker, another strong signal.
        if not filename:
            begin_file_matches = BEGIN_FILE_REGEX.findall(search_window)
            if begin_file_matches:
                # Take the last one found before the code block.
                candidate = begin_file_matches[-1].strip()
                if candidate: # Check it's not empty
                    filename = candidate

        # 3. Look for a filename in a markdown heading.
        if not filename:
            # We'll take the last one found before the code block.
            heading_matches = HEADING_FILENAME_REGEX.findall(search_window)
            if heading_matches:
                candidate = heading_matches[-1].strip()
                if is_plausible_filename(candidate):
                    filename = candidate

        # 4. Look for a line ending in `filename`:
        if not filename:
            line_ending_matches = LINE_ENDING_IN_FILENAME_REGEX.findall(search_window)
            if line_ending_matches:
                # Take the last one found before the code block.
                candidate = line_ending_matches[-1].strip()
                if is_plausible_filename(candidate):
                    filename = candidate

        # 5. If no heading match, infer from general context (backticked text).
        if not filename:
            context_filenames = FILENAME_REGEX.findall(search_window)
            if context_filenames:
                # Iterate in reverse to find the most recent plausible filename.
                for candidate in reversed(context_filenames):
                    candidate = candidate.strip()
                    if is_plausible_filename(candidate):
                        filename = candidate
                        break # Stop after finding the first plausible one from the end.

        # 6. Fallback: If still no filename, try to find one in code comments.
        if not filename:
            filename = extract_target_from_code(code)


        if lang in ('diff', 'patch'):
            # For diffs, the filename in the diff content is most reliable.
            # The filename from context/comments serves as a fallback.
            target_file = extract_target_from_diff(code) or filename
            if not target_file:
                summary_lines.append(f"-> SKIPPED: Could not determine target file for a diff block.")
                continue

            backup_info = ""
            if os.path.exists(target_file):
                backup_filename = f"{target_file}.bak"
                try:
                    shutil.copy2(target_file, backup_filename)
                    backup_info = f" (original saved to {backup_filename})"
                except Exception as e:
                    summary_lines.append(f"-> FAILED TO BACK UP: {target_file}\n   {e}")
                    continue

            success, message = apply_patch(target_file, code)
            if success:
                summary_lines.append(f"-> PATCHED: {target_file}{backup_info}")
            else:
                summary_lines.append(f"-> FAILED TO PATCH: {target_file}\n   {message}")

            # Replace the processed block in the displayed answer with a note.
            replacement_text = f"\n[... diff for {target_file} applied ...]\n"
            processed_answer = processed_answer[:match.start()] + replacement_text + processed_answer[match.end():]

        else: # Assumed to be a full file content block.
            target_file = filename
            if not target_file:
                # Use the whole 'language_info' for a more descriptive skip message.
                display_lang = language_info or 'unspecified'
                summary_lines.append(f"-> SKIPPED: Could not determine filename for a '{display_lang}' code block.")
                continue

            try:
                directory = os.path.dirname(target_file)
                if directory:
                    os.makedirs(directory, exist_ok=True)

                backup_info = ""
                if os.path.exists(target_file):
                    backup_filename = f"{target_file}.bak"
                    try:
                        shutil.copy2(target_file, backup_filename)
                        backup_info = f" (original saved to {backup_filename})"
                    except Exception as e:
                        summary_lines.append(f"-> FAILED TO BACK UP: {target_file}\n   {e}")
                        continue

                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                summary_lines.append(f"-> WROTE: {target_file}{backup_info}")

                replacement_text = f"\n[... content for {target_file} saved ...]\n"
                processed_answer = processed_answer[:match.start()] + replacement_text + processed_answer[match.end():]

            except Exception as e:
                summary_lines.append(f"-> FAILED TO WRITE: {target_file}\n   {e}")

    # Create the final summary and append it to the transcript file.
    summary = ""
    if summary_lines:
        summary = "--- WORK SUMMARY ---\n" + "\n".join(reversed(summary_lines))

        with open(transcript_path, 'a', encoding='utf-8') as f:
            f.write("\n\n")
            f.write(summary)

    return processed_answer, summary