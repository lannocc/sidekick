# Proposal: An Advanced Shell Parser for IOSK

**Status**: [alpha] coded and submitted for QA.

### Introduction

The current command parsing mechanism within the IOSK kernel is rudimentary, relying on simple string splitting (e.g., `args.split(' ')`). This approach is brittle and has several significant limitations:
1.  It cannot handle arguments that contain spaces, as there is no concept of quoting.
2.  It forces complex commands to implement their own argument parsing logic.
3.  It has led to command-specific hacks to implement core shell features, such as the manual variable substitution in `bin/echo.py`.

This proposal outlines a plan to implement a robust, centralized shell parser within the kernel. This change will make the command-line interface more powerful and reliable for both human and AI users, simplify the implementation of individual commands, and establish a foundation for future shell features like pipes and redirection.

### Core Goals

The new parser should achieve the following:
1.  **Robust Tokenization**: Correctly split a command string into a list of tokens, respecting single and double quotes to handle arguments with spaces.
2.  **Variable Expansion**: Automatically expand environment variables (e.g., `$USER`, `${PATH}`) before passing arguments to a command.
3.  **Alias Integration**: Cleanly integrate the existing alias expansion mechanism into the parsing pipeline.
4.  **Command Simplification**: Remove the need for parsing logic (string splitting, variable expansion) within individual command files.

### Proposed Implementation Strategy

We will modify the `IOSK.call` method in `src/iosk/kernel.py` to implement a multi-stage parsing pipeline. The key to robust tokenization will be leveraging Python's standard `shlex` library.

The new pipeline within `IOSK.call` will be as follows:

**1. Alias Expansion (Pre-Parsing)**
This step remains largely as-is. The raw command string is inspected. If the first word matches an alias in `io.aliases`, the raw string is rewritten using the alias's value. This ensures aliases can contain complex arguments and variables that will be correctly handled by the subsequent stages.

*   **Example**: `alias ll='ls -l'`. Input: `$ ll /home`.
*   The raw string becomes `'ls -l /home'` before being passed to the tokenizer.

**2. Tokenization with `shlex`**
The (potentially expanded) command string will be passed to `shlex.split()`. This function understands shell-like quoting rules and will reliably tokenize the input.

*   **Example**: `cp "my source file.txt" /tmp/`
*   `shlex.split()` will produce: `['cp', 'my source file.txt', '/tmp/']`.

**3. Variable Expansion**
After tokenization, the kernel will iterate through the resulting list of tokens. For each token, it will scan for and expand environment variables. This logic will use the `io.environ()` method to access the current context's environment. It should support both `$VAR` and `${VAR}` syntax.

*   **Example**: `echo "Welcome, $USER"` -> `['echo', 'Welcome, $USER']`
*   After expansion (assuming `io.user` is 'beta'): `['echo', 'Welcome, beta']`

**4. Command Dispatch**
After the pipeline completes, the first token in the list is the command to be executed, and the remaining tokens are its arguments. The kernel will use this clean, pre-processed list to invoke the command.

### Refactoring `iocall` and Command Signatures

To fully leverage the new parser, a breaking change to the `iocall` function signature in all `/bin/*.py` files is required. This will standardize argument passing and is crucial for simplifying command logic.

The current signature is:
`async def iocall(io, args: str)`

The proposed new signature is:
`async def iocall(io, argv: list)`

Under the new system, `argv` will be a list of strings representing the arguments *after* the command name itself.

*   **Example Command**: `$ cp original.txt "copy of original.txt"`
*   **Pipeline Output**: `['cp', 'original.txt', 'copy of original.txt']`
*   **Kernel Action**: The kernel identifies the command is `cp`, loads `/bin/cp.py`, and calls its `iocall` function.
*   **`iocall` Invocation**: `await py.iocall(io, ['original.txt', 'copy of original.txt'])`

### Impact and Benefits: Simplifying Commands

This refactoring will have a significant positive impact on the simplicity and consistency of all commands.

**Example 1: `bin/echo.py`**

*   **Before**: `echo.py` contains a complex `while '$' in args:` loop to manually find and replace environment variables.
*   **After**: The entire variable substitution hack is removed. The new `iocall` becomes trivial:
    ```python
    async def iocall(io, argv):
        await io.print(' '.join(argv))
        return True
    ```

**Example 2: `bin/cp.py`**

*   **Before**: The command must manually split its `args` string: `args = args.split(' ')`. This fails if a filename contains spaces.
*   **After**: The command receives a clean list. The logic becomes more robust and readable:
    ```python
    async def iocall(io, argv):
        if len(argv) != 2:
            await io.error('!! cp needs 2 arguments: <source> <destination>')
            return

        source = argv[0]
        destination = argv[1]
        # ... rest of the copy logic ...
    ```

### Conclusion

Adopting this advanced parser is a foundational improvement for IOSK. It will fix numerous bugs and limitations in the current system, drastically simplify the development of new and existing commands, and provide a more powerful and intuitive command-line experience. This change moves IOSK closer to a true, UNIX-like conversational OS and is a prerequisite for future enhancements such as I/O redirection and command pipes.
