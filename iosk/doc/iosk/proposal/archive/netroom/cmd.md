# IOSK Command-Line Entry Point (`iosk`)

### 1. Introduction

This document specifies the implementation of `sk/iosk/cmd.py`, which serves as the primary entry point for launching an IOSK system instance from a host shell (e.g., bash). As part of the Netroom architecture, this command's role is simplified and clarified: it is solely responsible for initializing the IOSK kernel and establishing the initial administrative console session for the `root` user.

This refactoring removes previous sub-commands and options, creating a single, predictable method for starting a local IOSK system. It paves the way for the `skh` client to become the standard for all other user connections.

### 2. Command-Line Interface

The `iosk` command, as defined in `setup.py`, directly executes the `run` function within `sk/iosk/cmd.py`. Its command-line interface is streamlined to a single required argument.

*   **Usage**:
    ```bash
    iosk <root_directory>
    ```

*   **Arguments**:
    *   `<root_directory>`: (Required) The path on the host filesystem that serves as the root (`/`) of the sandboxed IOSK environment.

*   **Options**:
    *   All previous options, including `-t` for "terminal mode," are deprecated. The `iosk` command is now exclusively for launching the local root console, which defaults to using the `/dev/console` device. The rich terminal experience previously associated with `/dev/terminal.py` is now the responsibility of the `skh` network client.

*   **Deprecation**:
    *   The `<handle>` argument is removed. The initial session is always for the `root` user.
    *   The `sk iosk <command>` syntax and its sub-commands (`run`, `shell`, `system`) are removed in favor of the direct `iosk` entry point with its singular function.

### 3. Core Implementation (`run` function)

The `run` function orchestrates the entire lifecycle of the IOSK system, from startup to graceful shutdown.

#### 3.1. Argument Parsing
1.  The `run` function receives the command-line arguments from `sys.argv`.
2.  It validates that exactly one argument, `<root_directory>`, is provided.
3.  If the argument count is incorrect, it prints a usage error and exits.

#### 3.2. System Initialization
1.  **Kernel Instantiation**: An instance of the `IOSK` kernel class (from `src/iosk/kernel.py`) is created, passing the `<root_directory>` to its constructor. The kernel is now solely responsible for instantiating its own subsystems, such as `AIMessenger`.

#### 3.3. Asynchronous Main Loop (`async_run`)
The core logic is contained within an `async def async_run()` function, executed via `asyncio.run()`.

1.  **Kernel Startup**: The `kernel.start()` coroutine is awaited. This method initializes the kernel state and its subsystems, increments the boot count, creates necessary directories (e.g., `/var/cache`), and executes the system initialization script at `/sbin/init`.

2.  **Root Session Coroutine**: A separate coroutine, `_run_console_session`, is defined to handle the `root` user's lifecycle:
    ```python
    async def _run_console_session(kernel):
        # Login the root user on the default console device.
        io = await kernel.login('root', device='/dev/console')
        if io:
            # Begin the interactive command loop, which blocks until logout.
            await kernel.interactive(io)
    ```

3.  **Task Creation**: The main system components are launched as concurrent `asyncio.Task`s:
    *   `unix_task = asyncio.create_task(kernel.run())`: This task runs the kernel's main lifecycle loop, which primarily waits for a shutdown signal (`kernel.halt` event).
    *   `console_task = asyncio.create_task(_run_console_session(kernel))`: This task manages the entire lifecycle of the `root` user's interactive session.

#### 3.4. Session and System Lifecycle Management
The system's execution is managed by waiting for the completion of the primary tasks.

1.  **Waiting for Exit**: The code awaits the completion of either `unix_task` or `console_task` using `asyncio.wait(..., return_when=asyncio.FIRST_COMPLETED)`.

2.  **Normal Logout**: If `console_task` finishes first, it signifies that the `root` user has logged out (e.g., by typing `$ exit` or pressing `Ctrl+D`). Since the root console is the only administrative interface, its termination signals the intent to shut down the entire system. The `run` function proceeds to set the kernel's shutdown event: `kernel.halt.set()`.

3.  **Shutdown Command**: If `unix_task` finishes first, it means `kernel.halt` was set by an internal command (i.e., `$ shutdown`). The program then proceeds to the cleanup phase.

#### 3.5. Graceful Shutdown and Cleanup
A robust `try...finally` block ensures a clean shutdown process.

1.  **Exception Handling**: `KeyboardInterrupt` (`Ctrl+C`) and `EOFError` (`Ctrl+D`) are caught to initiate a graceful shutdown by setting `kernel.halt.set()`.

2.  **Task Cleanup**: In the `finally` block, any remaining pending tasks are cancelled to prevent them from running after the main loop has exited.

3.  **Final Await**: The `unix_task` is awaited one last time. This gives the kernel a chance to complete its shutdown sequence, which includes logging out any remaining users and closing log files.

### 4. Interaction with Other Components

*   **`kernel.py`**: The `run` function acts as the master controller that starts the kernel via `kernel.start()` and manages its lifecycle via the `kernel.run()` task and the `kernel.halt` event. It initiates the `root` user session by calling `kernel.login()` and `kernel.interactive()`.
*   **`chat.py`**: The `run` function has no direct interaction with the chat subsystem. The `AIMessenger` is now a component managed internally by the kernel.
*   **`/dev/console.py`**: The `root` session is hardcoded to attach to the `/dev/console` device, which provides the basic, line-by-line terminal I/O via the `aioconsole` library.

