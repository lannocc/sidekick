# Copyright (C) 2025 LANNOCC
# @%@~LICENSE~@%@

import re
import shlex
import traceback
from typing import TYPE_CHECKING, Optional, List

# Prevent circular imports during runtime for type hints
if TYPE_CHECKING:
    from .kernel import IOSK
    from .io import Context

class CommandLineParser:
    """
    Handles command line parsing, including command substitution,
    variable expansion, and tokenization, adhering to shell-like
    quoting rules.
    """
    def __init__(self, iosk_kernel: 'IOSK'):
        """
        Initializes the parser with a reference to the IOSK kernel
        for recursive command execution during substitution.
        """
        self.os = iosk_kernel # Reference to the IOSK kernel instance

    async def _perform_command_substitution(self, io: 'Context', text: str) -> str:
        """
        Performs command substitution (`...` and $(...)) on a string.
        Substitution is prevented inside single quotes.
        """
        processed_text = ""
        pos = 0
        while pos < len(text):
            # Find the next potential start of a substitution
            try:
                backtick_pos = text.index('`', pos)
            except ValueError:
                backtick_pos = -1

            try:
                dollar_paren_pos = text.index('$(', pos)
            except ValueError:
                dollar_paren_pos = -1

            # Determine which comes first
            sub_start = -1
            is_backtick = False
            if backtick_pos != -1 and (dollar_paren_pos == -1 or backtick_pos < dollar_paren_pos):
                sub_start = backtick_pos
                is_backtick = True
            elif dollar_paren_pos != -1:
                sub_start = dollar_paren_pos

            if sub_start == -1:
                # No more substitutions found, append remaining text
                processed_text += text[pos:]
                break

            # Check quoting state at the substitution point by parsing the prefix
            # This simplified quote parsing handles single quotes preventing substitution
            current_segment_before_sub = text[pos:sub_start]
            state = 'NORMAL' # Can be NORMAL, IN_SINGLE_QUOTE, IN_DOUBLE_QUOTE
            is_escaped = False
            for char in current_segment_before_sub:
                if is_escaped:
                    is_escaped = False
                    continue
                if char == '\\':
                    is_escaped = True
                    continue

                if char == "'" and state != 'IN_DOUBLE_QUOTE':
                    state = 'IN_SINGLE_QUOTE' if state == 'NORMAL' else 'NORMAL'
                elif char == '"' and state != 'IN_SINGLE_QUOTE':
                    state = 'IN_DOUBLE_QUOTE' if state == 'NORMAL' else 'NORMAL'

            # Append the text before the potential substitution to processed_text
            processed_text += text[pos:sub_start]

            if state == 'IN_SINGLE_QUOTE':
                # Inside single quotes, treat substitution markers as literal
                if is_backtick:
                    processed_text += '`'
                    pos = sub_start + 1
                else: # $(
                    processed_text += '$('
                    pos = sub_start + 2
                continue

            # --- Valid substitution: find its end and extract inner command ---
            inner_command = None
            sub_end = -1

            if is_backtick:
                try:
                    sub_end = text.index('`', sub_start + 1)
                    inner_command = text[sub_start + 1 : sub_end]
                    pos = sub_end + 1
                except ValueError: # Unmatched backtick
                    await io.error("!! unmatched backtick in command substitution")
                    processed_text += '`' # Append literal backtick
                    pos = sub_start + 1
                    continue
            else: # $(...)
                level = 1
                scan_pos = sub_start + 2
                found_end = False
                # Simple paren-matching. Does not fully handle quotes/escapes inside.
                while scan_pos < len(text):
                    char = text[scan_pos]
                    if char == '(':
                        level += 1
                    elif char == ')':
                        level -= 1
                        if level == 0:
                            sub_end = scan_pos
                            inner_command = text[sub_start + 2 : sub_end]
                            pos = sub_end + 1
                            found_end = True
                            break
                    scan_pos += 1

                if not found_end: # Unmatched $(
                    await io.error("!! unmatched '$(' in command substitution")
                    processed_text += '$(' # Append literal $(
                    pos = sub_start + 2
                    continue

            if inner_command is None: continue # Should not happen if found_end is True

            # --- Execute the substitution's inner command ---
            io_sub = io.fork()
            io_sub.stage_pre() # Capture output to io_sub.pre StringIO buffer
            output = ""
            try:
                # Recursively call `self.os.call` to handle the inner command
                success = await self.os.call(io_sub, inner_command)
                output = io_sub.pre.getvalue().strip()
                if not success:
                    # If the inner command failed, output nothing for the substitution
                    # or an empty string, as per shell behavior.
                    output = ""
            except Exception as e:
                await io.error(f"!! error in command substitution `{inner_command}`: {e}")
                traceback.print_exc()
                output = ""
            finally:
                io_sub.stage_normal() # Restore staging for sub-context

            processed_text += output

        return processed_text

    def _expand_variables(self, text: str, env: dict) -> str:
        """
        Expands variables in a string (e.g., $VAR, ${VAR}),
        respecting single quotes (no expansion) and backslash escapes.
        Double quotes allow expansion.
        """
        result = []
        in_single_quotes = False
        in_double_quotes = False
        i = 0
        while i < len(text):
            char = text[i]

            if char == '\\':
                # Escapes are processed only outside single quotes
                if not in_single_quotes:
                    if i + 1 < len(text):
                        result.append(text[i+1]) # Append the escaped character
                        i += 2
                        continue
                    else: # Trailing escape character, keep it literal
                        result.append(char)
                        i += 1
                        continue
                else: # Inside single quotes, backslash is literal
                    result.append(char)
                    i += 1
                    continue

            if char == "'":
                if not in_double_quotes: # Single quotes don't nest or affect double quotes
                    in_single_quotes = not in_single_quotes
                result.append(char)
                i += 1
                continue

            if char == '"':
                if not in_single_quotes: # Double quotes don't nest or affect single quotes
                    in_double_quotes = not in_double_quotes
                result.append(char)
                i += 1
                continue

            if char == '$' and not in_single_quotes:
                # Handle variable expansion: $VAR or ${VAR}
                match = re.match(r'\$(\w+)|\$\{(\w+)\}', text[i:])
                if match:
                    var_name = match.group(1) or match.group(2)
                    value = env.get(var_name, '')
                    result.append(value)
                    i += match.end() # Advance past the matched variable
                    continue

            # Normal character
            result.append(char)
            i += 1

        return "".join(result)

    async def parse_and_tokenize(self, io: 'Context', command_line: str) -> Optional[List[str]]:
        """
        Orchestrates the full parsing process:
        1. Command Substitution
        2. Variable Expansion
        3. Tokenization using shlex.
        Returns a list of arguments (argv) or None if parsing fails.
        """
        # Step 1: Command Substitution (e.g., `cmd` or $(cmd))
        substituted_command_line = await self._perform_command_substitution(io, command_line)

        # Step 2: Variable Expansion (e.g., $VAR or ${VAR})
        # This occurs after command substitution, and on the result of that.
        expanded_command_line = self._expand_variables(substituted_command_line, io.environ())

        # Step 3: Tokenization using shlex.split
        # shlex.split handles quotes and escapes in the final expanded string.
        try:
            argv = shlex.split(expanded_command_line)
            return argv
        except ValueError as e:
            await io.error(f"!! parse error: {e}")
            return None

