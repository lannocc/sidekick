# sk/worker.py

import re
import os
import subprocess
import tempfile
import shutil

# Regex to find code blocks, adapted from sk/util.py to be non-greedy.
CODEBLOCK_REGEX = re.compile(r'```(?P<language>\w*?)\n(?P<code>.*?)\n```', re.DOTALL)

# Regex to find file paths in backticks, updated to allow spaces in the path.
FILENAME_REGEX = re.compile(r'`([^`]+)`')


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

        # Execute the system's `patch` command.
        result = subprocess.run(
            ['patch', target_file, diff_filename],
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
        lang = match.group('language').lower()
        code = match.group('code')
        original_block = match.group(0)

        # --- Filename Inference Logic ---
        # 1. Infer from context: Look for a filename in backticks in the line
        #    immediately preceding the code block.
        preceding_text = answer[:match.start()].rstrip()
        context = ""
        if preceding_text:
            last_line_start = preceding_text.rfind('\n') + 1
            context = preceding_text[last_line_start:]

        filename = None
        filename_match = FILENAME_REGEX.search(context)
        if filename_match:
            filename = filename_match.group(1)

        # 2. Fallback: If no filename was found in the context, try to find one
        #    commented in the first few lines of the code itself.
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
                summary_lines.append(f"-> SKIPPED: Could not determine filename for a '{lang}' code block.")
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