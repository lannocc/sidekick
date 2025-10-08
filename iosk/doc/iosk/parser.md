## CommandLineParser Class Summary

The `CommandLineParser` class is a crucial component of the IOSK kernel, specifically designed to handle the intricate process of parsing command-line input. It provides robust capabilities for command substitution, variable expansion, comment stripping, and tokenization, adhering to shell-like quoting rules. It also includes logic to deconstruct a fully tokenized command line into a pipeline of commands, ready for execution with I/O redirection and pipes. This centralizes complex parsing logic, simplifying individual command implementations and enhancing the overall power and reliability of the IOSK command-line interface.

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
        *   **Extraction**: Extracts the inner command string from between the delimiters, correctly handling nested substitutions for `$(...)`.
        *   **Execution**: Creates a forked `Context` (`io_sub`), redirects its `stdout` to an in-memory buffer to capture its output, and then recursively calls `self.os.call(io_sub, inner_command)` to execute the extracted command.
        *   **Replacement**: Replaces the original command substitution string with the captured `stdout` of the executed inner command, stripped of leading/trailing whitespace.
        *   **Error Handling**: Catches unmatched backticks or parentheses and reports errors using `io.error`, appending the literal substitution marker to the result.

*   `_expand_variables(self, text: str, env: dict) -> str`:
    *   **Purpose**: Expands environment variables within a given `text` string, supporting both `$VAR` and `${VAR}` syntax.
    *   **Behavior**:
        *   Iterates through the input `text` character by character.
        *   **Quote Awareness**: Prevents any variable expansion within single-quoted regions. Backslashes are also treated literally here. Double quotes allow variable expansion.
        *   **Escaping**: Handles backslash escapes (`\`) correctly when outside single quotes.
        *   **Substitution**: When a `$` is encountered outside single quotes, it attempts to match `$VAR` or `${VAR}` regex patterns. If a match is found, it looks up the `VAR` name in the provided `env` dictionary. If found, the variable is replaced by its value; otherwise, it's replaced by an empty string (standard shell behavior).

*   `_strip_comments(self, text: str) -> str`:
    *   **Purpose**: Removes comments from a command line. A comment is defined as the first unescaped, unquoted `#` character and all subsequent characters on the line.
    *   **Behavior**:
        *   Scans the input `text` while tracking the current quoting state (single or double quotes) and whether the previous character was an escape backslash.
        *   If a `#` is found outside of any quotes and is not escaped, the method returns the portion of the string that came before the `#`.

*   `async parse_and_tokenize(self, io: Context, command_line: str) -> Optional[List[str]]`:
    *   **Purpose**: Orchestrates the complete command-line parsing pipeline to produce a flat list of tokens.
    *   **Behavior**:
        1.  **Command Substitution**: Calls `_perform_command_substitution` on the input `command_line`.
        2.  **Variable Expansion**: Calls `_expand_variables` on the result of the substitution step.
        3.  **Comment Stripping**: Calls `_strip_comments` on the expanded string.
        4.  **Tokenization**: Uses `shlex.split()` on the fully processed string. `shlex.split()` is a robust Python standard library function that correctly handles shell-like quoting and backslash escapes to produce a clean list of arguments.
        *   **Error Handling**: Catches `ValueError` exceptions raised by `shlex.split()` (e.g., due to unmatched quotes) and reports them.

*   `async parse_pipeline(self, io: Context, command_line: str) -> Tuple[Optional[List[List[str]]], Optional[str], bool]`:
    *   **Purpose**: The main entry point for the `CommandPipelineExecutor`. It takes a raw command line and processes it into a structured representation of a command pipeline, including I/O redirection.
    *   **Behavior**:
        1.  **Tokenize**: First, it calls `parse_and_tokenize` to get a clean, flat list of all arguments.
        2.  **Split Pipeline**: It then iterates through this token list, splitting it into separate commands based on the pipe operator (`|`).
        3.  **Identify Redirection**: It also identifies output redirection operators (`>` for overwrite, `>>` for append) and extracts the target filename.
        *   **Error Handling**: Reports errors for syntax issues like empty commands before or after a pipe, or missing filenames for redirection.
    *   **Returns**: A tuple containing:
        *   A list of commands, where each command is itself a list of strings (`List[List[str]]`).
        *   The path for output redirection as a string, or `None`.
        *   A boolean indicating if the redirection mode is append (`True` for `>>`).
        If a parsing error occurs, the first element of the tuple will be `None`.

**Overall Purpose:**

The `CommandLineParser` acts as the intelligent front-end to command execution in IOSK. By centralizing complex parsing logic, it:
*   **Simplifies Command Implementations**: Commands in `/bin/*.py` (and scripts) no longer need to implement their own string splitting or variable expansion, receiving a clean `argv` list.
*   **Increases Robustness**: Correctly handles spaces in arguments, quoting, comments, and complex substitutions, preventing many common shell scripting errors.
*   **Enables Advanced Features**: Provides a solid foundation for advanced shell features like I/O redirection (`>`, `>>`) and piping (`|`) by transforming a raw command string into a structured, executable pipeline.
*   **Enhances AI Interaction**: Allows AI agents to construct more complex command lines, knowing they will be correctly interpreted by the system.
