# Proposal: A Process Management System for IOSK

**Status**: Proposed.

### Introduction

The current IOSK environment executes commands synchronously within a user's session. While effective for simple, short-lived tasks, this model lacks mechanisms for monitoring or managing command execution. AI agents, in particular, may initiate long-running or computationally intensive commands (e.g., a recursive search from the root directory) that can become stuck or consume indefinite time, rendering the agent unresponsive. Without a way to view and control these operations, system administrators lack the tools to ensure stability and manage agent behavior.

This proposal introduces a simple, UNIX-inspired process management system for IOSK. This system will track each command execution as a "process," making it visible through a `ps` command and manageable via a `kill` command. A `top` command will also be provided for a snapshot overview of system activity. This will provide administrators with essential visibility and control, enhancing the stability and manageability of the multi-agent environment.

### Core Concepts

1.  **IOSK "Process"**: An IOSK process is not a true operating system process. Instead, it is a lightweight wrapper that represents a single, ongoing command execution within a user's session. Each process will be defined by:
    *   **PID (Process ID)**: A unique, sequentially assigned integer.
    *   **User**: The username of the user who initiated the command.
    *   **Command**: The full command string that was executed.
    *   **Start Time**: The timestamp when the process began.
    *   **Task**: A reference to the underlying `asyncio.Task` that is running the command's logic.

2.  **Process Table**: The IOSK kernel will maintain a central, in-memory "process table"—a simple dictionary mapping PIDs to their corresponding Process objects. This table will be the single source of truth for all currently running commands.

3.  **Process Lifecycle**:
    *   **Creation**: When a user executes a command, the kernel's pipeline executor will create a new Process object, assign it a PID, and add it to the process table *before* the command's `iocall` is invoked.
    *   **Execution**: The process is considered "running" as long as its `asyncio.Task` is active.
    *   **Termination (Normal)**: Upon normal completion of the command, a `finally` block in the executor will ensure the process is removed from the process table.
    *   **Termination (Forced)**: The `kill` command will look up a PID, retrieve its associated `asyncio.Task`, and cancel it. The `finally` block in the executor will catch the `CancelledError` and perform the same cleanup, removing it from the process table.

### Implementation Strategy

#### 1. Kernel and Pipeline Modifications

*   **`src/iosk/kernel.py` - `IOSK` Class**:
    *   Add a process table and a PID counter to the `__init__` method:
        ```python
        self.process_table = {}
        self.next_pid = 1
        ```

*   **Process Data Structure**: A simple class will be defined (e.g., in a new `src/iosk/process.py` or within `kernel.py`) to hold process information.
    ```python
    class Process:
        def __init__(self, pid, user, command, start_time, task):
            self.pid = pid
            self.user = user
            self.command_str = ' '.join(command) # Store the command as a string
            self.start_time = start_time
            self.task = task
    ```

*   **`src/iosk/pipeline.py` - `CommandPipelineExecutor`**:
    *   The `_execute_single_command` method is the ideal place to manage the process lifecycle. It will be wrapped to handle process creation and cleanup.

    ```python
    # Conceptual change in CommandPipelineExecutor
    async def _execute_single_command(self, io: 'Context', argv: List[str]) -> bool:
        if not argv: return True
    
        # --- Process Creation ---
        pid = self.os.next_pid
        self.os.next_pid += 1
        
        # We need to create the task here to store it.
        # The command logic itself is now wrapped in a coroutine.
        command_coro = self._run_command_logic(io, argv)
        task = asyncio.create_task(command_coro)
    
        process = Process(pid, io.user, argv, datetime.now(), task)
        self.os.process_table[pid] = process
        
        try:
            # Await the task that is now being tracked.
            return await task
        except asyncio.CancelledError:
            await io.error(f"!! Process {pid} ({process.command_str}) cancelled.")
            return False
        finally:
            # --- Process Cleanup ---
            if pid in self.os.process_table:
                del self.os.process_table[pid]
    
    async def _run_command_logic(self, io: 'Context', argv: List[str]) -> bool:
        # The original logic from _execute_single_command goes here...
        # ... resolve command path, check if python module, etc. ...
        # ... try: await py_mod.iocall(io, cmd_args) ...
        # ... except Exception ...
    ```

#### 2. New Commands

*   **`/bin/ps.py`**:
    *   **Usage**: `ps`
    *   **Description**: Lists all currently running processes.
    *   **Implementation**: The `iocall` will access `io.os.process_table`. It will iterate through the dictionary, calculate the elapsed time for each process, and print a formatted table with headers: `PID`, `USER`, `TIME`, `COMMAND`.

*   **`/bin/kill.py`**:
    *   **Usage**: `kill <pid>`
    *   **Description**: Terminates a running process.
    *   **Implementation**:
        *   The `iocall` will parse the PID from `argv`.
        *   It will validate that the PID is an integer and exists as a key in `io.os.process_table`.
        *   If valid, it will retrieve the `Process` object and call `process.task.cancel()`.
        *   It will print a confirmation message, e.g., `:: Process <pid> cancelled.`.
        *   Error handling for invalid or non-existent PIDs is required.

*   **`/bin/top.py`**:
    *   **Usage**: `top`
    *   **Description**: Provides a single, non-interactive snapshot of system activity and running processes, sorted by runtime.
    *   **Implementation**:
        *   The `iocall` will gather system summary info: system uptime (from `io.os.started`), total users (`len(io.os.users)`), and total processes (`len(io.os.process_table)`).
        *   It will then retrieve all processes from the process table, calculate their runtimes, and sort them in descending order of runtime.
        *   Finally, it will print the summary followed by the formatted process list, mimicking the output of `top -b -n1`.

### Use Case Scenario

1.  An AI agent, `alpha`, is tasked with finding a specific configuration file, but doesn't know where it is. It executes a broad, time-consuming search: `$ search "db_password" /`
2.  An administrator, `root`, notices that `alpha` is not responding to other commands.
3.  `root` runs `$ ps` to check system activity. The output shows:
    ```
    PID   USER    TIME      COMMAND
    101   alpha   2m 15s    search db_password /
    ```
4.  Seeing the long-running process, `root` decides to terminate it to free up the agent.
    `$ kill 101`
5.  The system responds immediately:
    `:: Process 101 cancelled.`
6.  In `alpha`'s session, the `search` command is interrupted, and the agent receives an error message:
    `!! Process 101 (search db_password /) cancelled.`
7.  The agent `alpha` is now free to accept new commands. `root` can then instruct it to perform a more targeted search.

### Benefits

*   **System Stability**: Prevents runaway or stuck agent commands from deadlocking a user session or consuming resources indefinitely.
*   **Administrator Control**: Provides essential tools for human operators to monitor, understand, and manage the actions of all users, especially autonomous AI agents.
*   **Enhanced Visibility**: Offers a clear, real-time view into the system's internal operations, which is critical for debugging and performance analysis.
*   **Foundation for Job Control**: This implementation is a foundational step towards more advanced shell features like background processes (`&`), job control (`fg`, `bg`), and process prioritization.

