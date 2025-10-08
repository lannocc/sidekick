## CommandPipelineExecutor Class Summary

The `CommandPipelineExecutor` class is the central orchestrator for all command execution within the IOSK system. It resides in `src/iosk/pipeline.py` and is instantiated by the kernel. Its primary responsibility is to take a raw command-line string from the user, process it through a multi-stage pipeline, and manage its execution, including handling advanced shell features like aliases, I/O redirection, pipes, and process management. By centralizing this complex logic, it dramatically simplifies individual command implementations in `/bin` and provides a robust, UNIX-like command environment.

**Initialization:**

*   `__init__(self, iosk_kernel)`:
    *   Initializes the executor with a reference to the `IOSK` kernel instance. This reference is used to access system-level resources like the process table, command loaders (`pymod`, `exec`), and the filesystem sandbox (`box`).

**Methods:**

*   `async execute_pipeline(self, io: Context, raw_command_line: str, parser: CommandLineParser) -> bool`:
    *   **Purpose**: The main public entry point for executing any command line. It is called directly by `IOSK.call`.
    *   **Behavior**: It orchestrates a multi-step execution flow:
        1.  **Alias Resolution**: It first inspects the command line and expands any aliases found in the user's `io.aliases`. This happens *before* any other parsing, allowing aliases to contain complex arguments that are handled by the subsequent steps.
        2.  **Parsing**: It delegates the (potentially alias-expanded) command string to the `CommandLineParser`. The parser returns a structured representation of the command, including a list of commands for a pipeline (`List[List[str]]`), the path for any output redirection (`> file` or `>> file`), and the redirection mode (append or overwrite).
        3.  **Optimization**: If the parsed result is a single command with no redirection, it takes an optimized path by calling `_execute_single_command` directly.
        4.  **Full Pipeline Execution**: For commands involving pipes or redirection, it iterates through each command segment:
            *   **Context Forking**: For each command in the pipeline, it creates a new child `Context` using `io.fork()`. This is crucial for isolating I/O streams (`stdin`, `stdout`) for each command while allowing them to inherit the parent's environment (e.g., current working directory).
            *   **Pipe Handling**: It uses an in-memory `StringIO` buffer to connect commands. The `stdout` of one command is set to this buffer, and the `stdin` of the next command is set to read from the same buffer, effectively "piping" the data.
            *   **Redirection Handling**: For the *last* command in a pipeline, if output redirection is specified, it opens the target file on the host filesystem (in write or append mode). It automatically creates any necessary parent directories for the target file, improving robustness. The command's `stdout` is then set to this file handle, directing all its output to the file instead of the console.
        *   **Error Handling**: If any command in the pipeline fails, the execution of the entire pipeline is halted immediately.

*   `async _execute_single_command(self, io: Context, argv: List[str]) -> bool`:
    *   **Purpose**: To wrap the execution of a single command segment within the IOSK process management framework.
    *   **Behavior**: This method is responsible for the **Process Lifecycle**:
        1.  **Process Creation**: It assigns a new, unique Process ID (PID) from the kernel's counter.
        2.  **Task Wrapping**: It wraps the core command logic (from `_run_command_logic`) into an `asyncio.Task`.
        3.  **Registration**: It creates a `Process` object containing the PID, user, command string, start time, and a reference to the `asyncio.Task`. This object is then added to the kernel's global `process_table`, making the command visible to tools like `ps`.
        4.  **Execution and Cleanup**: It awaits the completion of the task. Crucially, it uses a `finally` block to guarantee that the `Process` object is removed from the `process_table` when the command finishes, whether it succeeds, fails, or is cancelled.
        5.  **Cancellation Handling**: It specifically catches `asyncio.CancelledError`, which allows the `kill` command to gracefully terminate a running command by cancelling its underlying task.

*   `async _run_command_logic(self, io: Context, argv: List[str]) -> bool`:
    *   **Purpose**: The final stage of the pipeline, responsible for resolving the command name to an executable file and dispatching it.
    *   **Behavior**:
        1.  **Path Resolution**: It determines the full path to the command. It correctly handles absolute paths (`/bin/ls`), relative paths (`./myscript`), and searches the directories listed in the `PATH` environment variable for the command.
        2.  **Executable Prioritization**: When searching for a command (e.g., `ls`), it first checks for a corresponding Python module file (`ls.py`). If found, it is prioritized. If not, it then checks for a script file with the exact name (`ls`). This matches the kernel's `which` command logic.
        3.  **Dispatch**:
            *   If the resolved path points to a Python module, it is loaded using `self.os.pymod`, and its `iocall(io, argv)` method is called.
            *   If the path points to a script (e.g., a `skrip` file), it is executed via `self.os.exec`, which correctly handles shebang interpretation (`#!/bin/skrip`).
        *   **Error Handling**: It reports errors if a command cannot be found or if an exception occurs during its execution.

**Overall Purpose:**

The `CommandPipelineExecutor` is the engine of the IOSK shell. It acts as the critical link between the `CommandLineParser` and the individual command implementations. By handling the complexities of alias expansion, pipes, redirection, and process management, it allows command developers to focus solely on their command's logic, receiving a clean context and argument list (`argv`). This centralized, robust design is what enables the IOSK shell to provide powerful, flexible, and reliable command-line functionality.
