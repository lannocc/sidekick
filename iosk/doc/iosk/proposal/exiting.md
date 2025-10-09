# Proposal: Standardizing Session Termination and Interrupt Handling

**Status**: Proposed

### 1. Introduction

The current IOSK console provides a functional session for the `root` user, but its handling of session termination (`Ctrl+D`) and interrupts (`Ctrl+C`) is not fully aligned with user expectations for a modern, robust shell. Logging out the `root` user currently terminates the entire system, preventing a "headless" operational mode. Furthermore, the role of `Ctrl+C` is not clearly defined, leading to potential ambiguity between interrupting a command and exiting the shell.

This proposal outlines a plan to standardize interrupt and session termination handling for the IOSK console. It defines clear, distinct roles for `Ctrl+C` and `Ctrl+D`, introduces `exit` and `logout` as explicit session termination commands, and refactors the system lifecycle to allow the IOSK kernel to continue running after the `root` user has logged out. This will make the console experience more intuitive, robust, and aligned with standard UNIX shell conventions, while enabling a persistent, headless server mode.

### 2. Summary of Changes

*   **`Ctrl+C` (Interrupt)**: Will be used exclusively to interrupt the currently running command. It will **never** terminate the user's session or the system.
*   **`Ctrl+D` (End of File/Session)**: At an empty prompt, this will terminate the current user's session (i.e., log them out). The IOSK system itself will remain running.
*   **`exit` and `logout` Commands**: These will be introduced as built-in shell commands that are functionally identical to pressing `Ctrl+D` at a prompt, providing an explicit way to end a session.
*   **Headless Operation**: After the `root` console user logs out, the IOSK system will continue to run in a "headless" state, with its network `port` and AI agents remaining active.
*   **Host-Level Shutdown Signals**: Once the system is headless, new behaviors for `Ctrl+C` and `Ctrl+D` will be defined at the host terminal level to provide mechanisms for graceful and immediate system shutdown.

### 3. Detailed Specification

#### 3.1. Interrupt Handling (`Ctrl+C`)

The `Ctrl+C` signal (`KeyboardInterrupt`) will be handled contextually to provide non-destructive interruption, consistent with standard shells.

*   **When a command is running**:
    *   **Behavior**: The `KeyboardInterrupt` will be caught by the `CommandPipelineExecutor` (`src/iosk/pipeline.py`). It will cancel the `asyncio.Task` associated with the running command, effectively killing the process.
    *   **User Feedback**: The user will see `^C` printed to their console, followed by a message indicating the process was cancelled, and will be returned to a fresh shell prompt.
    *   **Implementation**: The existing `try...except KeyboardInterrupt` block in `_execute_single_command` already implements this correctly. This behavior will be preserved.

*   **When at an idle prompt**:
    *   **Behavior**: The `KeyboardInterrupt` will be caught by the main `interactive` loop in `src/iosk/kernel.py`. It will perform no action other than abandoning the current empty prompt line.
    *   **User Feedback**: The user will see `^C` printed, followed immediately by a new, fresh prompt on the next line. The session will not be terminated.
    *   **Implementation**: The existing `try...except KeyboardInterrupt` block in `interactive()` already implements this. This behavior will be preserved and formalized.

#### 3.2. Session Termination (`Ctrl+D`, `exit`, `logout`)

Terminating a user session will be a distinct action that logs the user out but does not affect the running state of the IOSK system.

*   **`Ctrl+D` (EOFError)**:
    *   **Behavior**: When the user presses `Ctrl+D` at an empty prompt, the I/O layer (`aioconsole` or `prompt_toolkit`) raises an `EOFError`. This will be caught by the `interactive` loop in `kernel.py`.
    *   **Implementation**: The `try...except EOFError` block in `interactive()` will be modified to simply `return`, gracefully ending the loop and thus the user's session.

*   **`exit` and `logout` Commands**:
    *   **Behavior**: These will be treated as built-in shell keywords, functionally identical to `Ctrl+D`.
    *   **Implementation**: The command processing logic within the `interactive()` loop in `kernel.py` will be modified to check for these commands *before* passing the line to the `call` method.
    ```python
    # Proposed change in src/iosk/kernel.py, inside interactive() loop
    if line in ('$ exit', '$ logout'):
        return # Terminate the interactive session
    
    # ... existing command processing logic ...
    ```

#### 3.3. System Lifecycle and Headless Operation

The most significant change is to decouple the root console session from the system's lifecycle, enabling a headless mode. This requires modifying the main entry point.

*   **File to Modify**: `src/iosk/cmd.py`
*   **Current Behavior**: The `async_run` function waits for either the `console_task` or `unix_task` to complete. If the `console_task` finishes (user logs out), it triggers a system shutdown (`kernel.halt.set()`).
*   **Proposed Behavior**: The `async_run` function will be refactored to explicitly manage two phases: the active console phase and the subsequent headless phase.

    ```python
    # Conceptual change in src/iosk/cmd.py
    async def async_run():
        # ... kernel startup ...
        unix_task = asyncio.create_task(kernel.run())
        console_task = asyncio.create_task(_run_console_session(kernel))

        # --- Phase 1: Active Console Session ---
        await console_task # Wait for the root user to log out.
        
        # --- Phase 2: Headless Operation ---
        print('\n:: Root console disconnected. System running in headless mode.')
        print(':: Press Ctrl+D for graceful shutdown, or Ctrl+C for immediate exit.')

        try:
            # The kernel is still running. We wait here for a host signal.
            # The only way to exit now is a KeyboardInterrupt or EOFError
            # from the host terminal.
            await unix_task 
        except (KeyboardInterrupt, EOFError) as e:
            # This block now ONLY executes after the user has logged out.
            if isinstance(e, EOFError):
                # Ctrl+D: Graceful Shutdown
                print('\n:: Graceful shutdown initiated by host signal.')
                if not kernel.halt.is_set():
                    kernel.halt.set()
                # Wait for kernel to finish its shutdown sequence
                await unix_task
            elif isinstance(e, KeyboardInterrupt):
                # Ctrl+C: Immediate Shutdown
                print('\n:: Immediate shutdown initiated by host signal.')
                if not unix_task.done():
                    unix_task.cancel()
    ```

### 4. User Experience and Command Summary

| Action                        | Context                     | Behavior                                                              | System State Change       |
| :---------------------------- | :-------------------------- | :-------------------------------------------------------------------- | :------------------------ |
| `Ctrl+C`                      | Command is running          | Interrupts and kills the running command; returns to prompt.          | None                      |
| `Ctrl+C`                      | At idle prompt              | Abandons current line, displays `^C` and a new prompt.                | None                      |
| `Ctrl+D` / `$ exit` / `$ logout` | At idle prompt (console active) | Logs out the current user; ends the console session.                  | User logged out; system continues running headless. |
| `Ctrl+D`                      | Host terminal (console inactive) | Initiates a **graceful** system shutdown (runs shutdown sequence).    | System shuts down.        |
| `Ctrl+C`                      | Host terminal (console inactive) | Initiates an **immediate** system shutdown (hard stop).               | System shuts down.        |
| `$ shutdown`                  | At idle prompt (console active) | Initiates a **graceful** system shutdown from within the session.     | System shuts down.        |

### 5. Conclusion

This proposal establishes a clear, predictable, and powerful model for session and process control within IOSK. By aligning `Ctrl+C` and `Ctrl+D` with UNIX conventions, we make the system more intuitive for experienced users. Most importantly, by decoupling the `root` session from the system lifecycle, we enable a critical new capability: persistent, headless operation. This transforms IOSK from a transient, single-session tool into a true background service, capable of running network services and autonomous AI agents indefinitely, even without an active administrative console.

