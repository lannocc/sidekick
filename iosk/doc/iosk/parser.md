## CommandLineParser Class Summary

The `CommandLineParser` class is a crucial component of the IOSK kernel, specifically designed to handle the intricate process of parsing command-line input. It provides robust capabilities for command substitution, variable expansion, and tokenization, adhering to shell-like quoting rules. This centralizes complex parsing logic, simplifying individual command implementations and enhancing the overall power and reliability of the IOSK command-line interface.

**Initialization:**

*   `__init__(self, iosk_kernel)`:
    *   Initializes the `CommandLineParser` with a reference to the `IOSK` kernel instance (`iosk_kernel`). This reference is essential for the parser to recursively call the kernel's `call` method during command substitution (e.g., when evaluating `$(command)`).
    *   Stores the kernel reference in `self.os`.

**Methods:**

*   `async _perform_command_substitution(self, io: Context, text: str) -> str`:
    *   **Purpose**: Processes command substitution within a given `text` string. This method identifies and executes commands enclosed in backticks (`` `command` ``) or dollar-parentheses (`$(command)`).
    *   **Behavior**:
        *   Iterates through the input `text` to find instances of `` ` `` or `$( `.
        *   **Quote Awareness**: Crucially, it prevents command substitution from occurring when inside single quotes (`'`). Double quotes (`"`) *do* allow command substitution.
        *   **Extraction**: Extracts the inner command string from between the delimiters.
        *   **Execution**: Creates a forked `Context` (`io_sub`), sets it to `STAGE_PRE` to capture its output, and then recursively calls `self.os.call(io_sub, inner_command)` to execute the extracted command.
        *   **Replacement**: Replaces the original command substitution string with the captured `stdout` of the executed inner command, stripped of leading/trailing whitespace.
        *   **Error Handling**: Catches unmatched backticks or parentheses and reports errors using `io.error`, appending the literal substitution marker to the result.
    *   **Parameters**:
        *   `io` (`Context`): The current execution context, used for error reporting and forking a sub-context for command execution.
        *   `text` (`str`): The command line string (or part of it) on which to perform substitutions.
    *   **Returns**: `str` - The string with all valid command substitutions performed.

*   `_expand_variables(self, text: str, env: dict) -> str`:
    *   **Purpose**: Expands environment variables within a given `text` string, supporting both `$VAR` and `${VAR}` syntax.
    *   **Behavior**:
        *   Iterates through the input `text` character by character.
        *   **Quote Awareness**:
            *   **Single Quotes (`'`):** Prevents any variable expansion within single-quoted regions. Backslashes are also treated literally here.
            *   **Double Quotes (`"`):** Allows variable expansion.
        *   **Escaping**: Handles backslash escapes (`\`) correctly when outside single quotes.
        *   **Substitution**: When a `$` is encountered outside single quotes, it attempts to match `$VAR` or `${VAR}` regex patterns. If a match is found, it looks up the `VAR` name in the provided `env` dictionary. If found, the variable is replaced by its value; otherwise, it's replaced by an empty string (standard shell behavior).
    *   **Parameters**:
        *   `text` (`str`): The string on which to perform variable expansion.
        *   `env` (`dict`): A dictionary of environment variables (typically from `io.environ()`).
    *   **Returns**: `str` - The string with all valid variables expanded.

*   `async parse_and_tokenize(self, io: Context, command_line: str) -> Optional[List[str]]`:
    *   **Purpose**: Orchestrates the complete command-line parsing pipeline. This is the primary public method of the `CommandLineParser`.
    *   **Behavior**:
        1.  **Command Substitution**: First, it calls `_perform_command_substitution` on the input `command_line` to handle any backtick or dollar-parentheses substitutions.
        2.  **Variable Expansion**: Next, it calls `_expand_variables` on the result of the substitution step, using the `io.environ()` to resolve variable values. This ensures that variables embedded within substitution results are also expanded.
        3.  **Tokenization**: Finally, it uses `shlex.split()` on the fully expanded string. `shlex.split()` is a robust Python standard library function that correctly handles shell-like quoting rules (single and double quotes) and backslash escapes to produce a clean list of arguments.
        *   **Error Handling**: Catches `ValueError` exceptions raised by `shlex.split()` (e.g., due to unmatched quotes) and reports them using `io.error`.
    *   **Parameters**:
        *   `io` (`Context`): The current execution context, used for accessing environment variables and reporting errors.
        *   `command_line` (`str`): The raw command line string provided by the user or an internal script (after alias resolution).
    *   **Returns**: `Optional[List[str]]` - A list of strings (`argv`) representing the tokenized arguments, or `None` if a parsing error occurred.

**Overall Purpose:**

The `CommandLineParser` acts as the intelligent front-end to command execution in IOSK. By centralizing complex parsing logic, it:
*   **Simplifies Command Implementations**: Commands in `/bin/*.py` (and scripts) no longer need to implement their own string splitting or variable expansion, receiving a clean `argv` list.
*   **Increases Robustness**: Correctly handles spaces in arguments, quoting, and complex substitutions, preventing many common shell scripting errors.
*   **Enables Advanced Features**: Provides a solid foundation for future shell features like I/O redirection and piping, as the output of this parser is a clean, reliable list of arguments.
*   **Enhances AI Interaction**: Allows AI agents to construct more complex command lines, knowing they will be correctly interpreted by the system.
