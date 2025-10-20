# src/iosk/parser.py
import re
import shlex
import traceback
from typing import TYPE_CHECKING, Optional, List, Tuple
from io import StringIO

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

    def _add_spaces_around_operators(self, text: str) -> str:
        """
        Adds spaces around unquoted, unescaped `|`, `>`, and `>>` operators.
        This is a pre-processing step for shlex.split to ensure these operators
        are treated as separate tokens.
        """
        result = []
        in_single_quotes = False
        in_double_quotes = False
        is_escaped = False  # Tracks if the character *after* a backslash should be treated literally

        i = 0
        while i < len(text):
            char = text[i]

            if is_escaped:
                result.append(char)
                is_escaped = False
                i += 1
                continue

            if char == '\\' and not in_single_quotes:
                is_escaped = True
                result.append(char)
                i += 1
                continue

            if char == "'" and not in_double_quotes:
                in_single_quotes = not in_single_quotes

            if char == '"' and not in_single_quotes:
                in_double_quotes = not in_double_quotes

            if not in_single_quotes and not in_double_quotes:
                if text[i:i+2] == '>>':
                    result.append(' >> ')
                    i += 2
                    continue
                if char in ('>', '|'):
                    result.append(f' {char} ')
                    i += 1
                    continue

            result.append(char)
            i += 1

        return "".join(result)

    async def _perform_command_substitution(self, io: 'Context', text: str) -> str:
        """
        Performs command substitution (`...` and $(...)) on a string.
        Substitution is prevented inside single quotes or if the marker is escaped.
        """
        processed_text = ""
        pos = 0
        while pos < len(text):
            backtick_pos = -1
            dollar_paren_pos = -1

            # Scan for the next unescaped, un-single-quoted backtick or $(
            scan_idx = pos
            in_single_quotes = False
            in_double_quotes = False
            is_escaped = False # Tracks if the *previous* character was a non-quoted backslash

            while scan_idx < len(text):
                char = text[scan_idx]
                if is_escaped:
                    is_escaped = False
                elif char == '\\' and not in_single_quotes:
                    is_escaped = True
                elif char == "'" and not in_double_quotes and not is_escaped:
                    in_single_quotes = not in_single_quotes
                elif char == '"' and not in_single_quotes and not is_escaped:
                    in_double_quotes = not in_double_quotes

                # --- FIX: Allow substitution inside double quotes ---
                if not in_single_quotes and not is_escaped:
                    if char == '`':
                        backtick_pos = scan_idx
                        break
                    if char == '$' and scan_idx + 1 < len(text) and text[scan_idx+1] == '(':
                        dollar_paren_pos = scan_idx
                        break
                scan_idx += 1

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

            # Append the text before the substitution marker
            processed_text += text[pos:sub_start]

            # --- Valid substitution: find its end and extract inner command ---
            inner_command = None
            sub_end = -1

            # --- FIX: Use local state variables for inner scan to prevent bugs ---
            in_single_quotes_inner = False
            in_double_quotes_inner = False
            is_escaped_inner = False

            if is_backtick:
                scan_pos = sub_start + 1
                found_end = False
                while scan_pos < len(text):
                    char = text[scan_pos]
                    if is_escaped_inner:
                        is_escaped_inner = False
                    elif char == '\\' and not in_single_quotes_inner:
                        is_escaped_inner = True
                    elif char == "'" and not in_double_quotes_inner and not is_escaped_inner:
                        in_single_quotes_inner = not in_single_quotes_inner
                    elif char == '"' and not in_single_quotes_inner and not is_escaped_inner:
                        in_double_quotes_inner = not in_double_quotes_inner
                    elif char == '`' and not in_single_quotes_inner and not is_escaped_inner:
                        sub_end = scan_pos
                        inner_command = text[sub_start + 1 : sub_end]
                        pos = sub_end + 1
                        found_end = True
                        break
                    scan_pos += 1

                if not found_end: # Unmatched backtick
                    await io.error("!! unmatched backtick in command substitution")
                    processed_text += '`' # Append literal backtick
                    pos = sub_start + 1
                    continue
            else: # $(...)
                level = 1
                scan_pos = sub_start + 2
                found_end = False
                while scan_pos < len(text):
                    char = text[scan_pos]
                    if is_escaped_inner:
                        is_escaped_inner = False
                    elif char == '\\' and not in_single_quotes_inner:
                        is_escaped_inner = True
                    elif char == "'" and not in_double_quotes_inner and not is_escaped_inner:
                        in_single_quotes_inner = not in_single_quotes_inner
                    elif char == '"' and not in_single_quotes_inner and not is_escaped_inner:
                        in_double_quotes_inner = not in_double_quotes_inner
                    elif char == '(' and not in_single_quotes_inner and not is_escaped_inner:
                        level += 1
                    elif char == ')' and not in_single_quotes_inner and not is_escaped_inner:
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

            if inner_command is None: continue

            # --- Execute the substitution's inner command ---
            io_sub = io.fork()
            io_sub.stdout = StringIO() # Capture output for substitution
            output = ""
            try:
                # Recursively call `self.os.call` to handle the inner command
                success = await self.os.call(io_sub, inner_command)
                output = io_sub.stdout.getvalue().strip()
                if not success:
                    # If the inner command failed, output nothing for the substitution
                    # or an empty string, as per shell behavior.
                    output = ""
            except Exception as e:
                await io.error(f"!! error in command substitution `{inner_command}`: {e}")
                traceback.print_exc()
                output = ""

            processed_text += output

        return processed_text

    def _expand_variables(self, text: str, env: dict) -> str:
        """
        Expands variables in a string (e.g., $VAR, ${VAR}).
        Respects single quotes (no expansion) and backslash escapes (prevent expansion).
        Double quotes allow expansion. Backslashes and hashes are passed literally.
        """
        result = []
        in_single_quotes = False
        in_double_quotes = False
        is_escaped = False # Tracks if the *previous* character was a non-quoted backslash

        i = 0
        while i < len(text):
            char = text[i]

            # Determine if the current char is escaped by a preceding backslash
            # (only if not inside single quotes)
            if is_escaped:
                is_escaped = False # Consume the escape for the current char
            elif char == '\\' and not in_single_quotes:
                is_escaped = True

            # Quoting rules: Single quotes disable everything. Double quotes disable most.
            if char == "'" and not in_double_quotes and not is_escaped:
                in_single_quotes = not in_single_quotes
            elif char == '"' and not in_single_quotes and not is_escaped:
                in_double_quotes = not in_double_quotes
            elif char == '$' and not in_single_quotes and not is_escaped:
                # Handle variable expansion: $VAR or ${VAR}
                match = re.match(r'\$(\w+)|\$\{(\w+)\}', text[i:])
                if match:
                    var_name = match.group(1) or match.group(2)
                    value = env.get(var_name, '')
                    result.append(value)
                    i += match.end() # Advance past the matched variable
                    continue # Continue to next char after var

            # Append the character as is. Escaping and quoting will be fully handled by shlex.split.
            result.append(char)
            i += 1

        return "".join(result)

    def _strip_comments(self, text: str) -> str:
        """
        Removes the first unescaped, unquoted '#' and everything after it.
        """
        in_single_quotes = False
        in_double_quotes = False
        is_escaped = False # Tracks if the *previous* character was a non-quoted backslash

        for i, char in enumerate(text):
            if is_escaped:
                is_escaped = False # The current character was escaped, so it's literal. Reset for next.
                # Continue processing to correctly identify quotes/escapes for subsequent chars if needed,
                # but this specific `char` won't trigger comment logic.
                continue

            if char == '\\':
                if not in_single_quotes: # Only a backslash outside single quotes can escape the next char
                    is_escaped = True
                continue # Keep the backslash; shlex.split will handle it

            if char == "'":
                if not in_double_quotes:
                    in_single_quotes = not in_single_quotes
                continue

            if char == '"':
                if not in_single_quotes:
                    in_double_quotes = not in_double_quotes
                continue

            if char == '#' and not in_single_quotes and not in_double_quotes:
                # Found an unescaped, unquoted comment character
                return text[:i].rstrip() # Return string up to this point, removing any trailing whitespace just before '#'

        return text # No comment found, return original text

    async def parse_and_tokenize(self, io: 'Context', command_line: str) -> Optional[List[str]]:
        """
        Orchestrates the full parsing process:
        1. Command Substitution
        2. Variable Expansion
        3. Comment Stripping
        4. Add spaces around operators to prepare for shlex
        5. Tokenization using shlex.
        Returns a list of arguments (argv) or None if parsing fails.
        """
        # Step 1: Command Substitution (e.g., `cmd` or $(cmd))
        substituted_command_line = await self._perform_command_substitution(io, command_line)

        # Step 2: Variable Expansion (e.g., $VAR or ${VAR})
        expanded_command_line = self._expand_variables(substituted_command_line, io.environ())

        # Step 3: Comment Stripping
        comment_stripped_line = self._strip_comments(expanded_command_line)

        # Step 4: Add spaces around operators to help shlex tokenize correctly.
        spaced_line = self._add_spaces_around_operators(comment_stripped_line)

        # Step 5: Tokenization using shlex.split
        # shlex.split handles quotes and escapes in the final string,
        # now that comments are pre-stripped.
        try:
            # comments=False (default) is crucial here to ensure `\` escapes are processed by shlex
            argv = shlex.split(spaced_line, comments=False)
            return argv
        except ValueError as e:
            await io.error(f"!! parse error: {e}")
            return None

    async def parse_pipeline(self, io: 'Context', command_line: str) -> Tuple[Optional[List[List[str]]], Optional[str], bool]:
        """
        Parses a command line into a pipeline of commands and identifies I/O redirection.
        Returns a tuple of (commands, redirect_path, append_mode).
        On parsing error, the 'commands' list will be None.
        """
        argv = await self.parse_and_tokenize(io, command_line)
        if argv is None: # A parsing error occurred and has been reported by the parser
            return None, None, False
        if not argv: # Empty command line is valid, but results in no commands
            return [], None, False

        # Step 2: Split the token list into a pipeline of commands and identify redirection
        commands = []
        current_command = []
        redirect_out_path = None
        redirect_append = False

        i = 0
        while i < len(argv):
            token = argv[i]
            if token == '|':
                if not current_command:
                    await io.error("!! parse error: empty command before pipe")
                    return None, None, False
                commands.append(current_command)
                current_command = []
            elif token in ('>', '>>'):
                if i + 1 >= len(argv):
                    await io.error(f"!! parse error: missing filename for redirection '{token}'")
                    return None, None, False
                if redirect_out_path:
                    await io.error("!! parse error: multiple redirections are not supported")
                    return None, None, False
                redirect_out_path = argv[i+1]
                redirect_append = (token == '>>')
                i += 1 # Skip the filename token
            else:
                current_command.append(token)
            i += 1

        if current_command:
            commands.append(current_command)
        elif commands and not redirect_out_path: # Case like `ls |`
            await io.error("!! parse error: empty command after pipe")
            return None, None, False

        if not commands and redirect_out_path:
             await io.error("!! parse error: redirection with no command")
             return None, None, False

        return commands, redirect_out_path, redirect_append

