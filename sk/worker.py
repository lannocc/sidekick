# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import re
import os
import subprocess
import tempfile
import shutil

# Regex to find code blocks, adapted from sk/util.py to be non-greedy.
CODEBLOCK_REGEX = re.compile(r'```(?P<language>\w*?)\n(?P<code>.*?)\n```', re.DOTALL)

# Regex to find file paths in backticks, used to infer filenames from context.
FILENAME_REGEX = re.compile(r'`([^`\s]+)`')


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

        # Infer filename from the context (one line) preceding the code block.
        context_start = answer.rfind('\n', 0, match.start()) + 1
        context = answer[context_start : match.start()].strip()

        filename = None
        filename_match = FILENAME_REGEX.search(context)
        if filename_match:
            filename = filename_match.group(1)

        if lang in ('diff', 'patch'):
            # The most reliable source for the filename is the diff content itself.
            target_file = extract_target_from_diff(code) or filename
            if not target_file:
                summary_lines.append(f"-> SKIPPED: Could not determine target file for a diff block.")
                continue

            if os.path.exists(target_file):
                backup_filename = f"{target_file}.bak"
                try:
                    shutil.copy2(target_file, backup_filename)
                    summary_lines.append(f"-> BACKED UP: {target_file} to {backup_filename}")
                except Exception as e:
                    summary_lines.append(f"-> FAILED TO BACK UP: {target_file}\n   {e}")
                    continue

            success, message = apply_patch(target_file, code)
            if success:
                summary_lines.append(f"-> PATCHED: {target_file}")
            else:
                summary_lines.append(f"-> FAILED TO PATCH: {target_file}\n   {message}")

            # Replace the processed block in the displayed answer with a note.
            replacement_text = f"\n[... diff for {target_file} applied ...]\n"
            processed_answer = processed_answer[:match.start()] + replacement_text + processed_answer[match.end():]

        else: # Assumed to be a full file content block.
            if not filename:
                summary_lines.append(f"-> SKIPPED: Could not determine filename for a '{lang}' code block.")
                continue

            try:
                directory = os.path.dirname(filename)
                if directory:
                    os.makedirs(directory, exist_ok=True)

                if os.path.exists(filename):
                    backup_filename = f"{filename}.bak"
                    try:
                        shutil.copy2(filename, backup_filename)
                        summary_lines.append(f"-> BACKED UP: {filename} to {backup_filename}")
                    except Exception as e:
                        summary_lines.append(f"-> FAILED TO BACK UP: {filename}\n   {e}")
                        continue

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(code)
                summary_lines.append(f"-> WROTE: {filename}")

                replacement_text = f"\n[... content for {filename} saved ...]\n"
                processed_answer = processed_answer[:match.start()] + replacement_text + processed_answer[match.end():]

            except Exception as e:
                summary_lines.append(f"-> FAILED TO WRITE: {filename}\n   {e}")

    # Create the final summary and append it to the transcript file.
    summary = ""
    if summary_lines:
        summary = "--- WORK SUMMARY ---\n" + "\n".join(reversed(summary_lines))

        with open(transcript_path, 'a', encoding='utf-8') as f:
            f.write("\n\n")
            f.write(summary)

    return processed_answer, summary

