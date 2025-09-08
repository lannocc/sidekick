## IOSK Daemons: A Proposal for Event-Driven AI Agents

### Introduction

The core philosophy of IOSK is to create a conversational operating system where interactions are intelligent and context-aware. To further this goal, we propose a "daemon" system. Unlike traditional UNIX daemons, which are long-running background processes, IOSK daemons are **event-driven AI agents**. They act as hooks into the kernel's workflow, waking up to perform specific, intelligent tasks in response to system events.

This system allows for powerful automation that goes beyond simple scripting. By leveraging AI agents as handlers, daemons can perform context-aware actions, making the OS feel more proactive and integrated.

### Core Concepts

1.  **Events**: Pre-defined hooks within the IOSK kernel's lifecycle or command execution flow. These are the triggers for daemons. Examples include:
    *   `POST_CODE_SAVE`: Fired after a code block from an AI's response is saved to a file.
    *   `USER_LOGIN`: Fired after a user successfully logs in.
    *   `PRE_COMMAND_EXEC`: Fired just before a user's command is executed.
    *   `PRE_SHUTDOWN`: Fired when the system shutdown sequence is initiated.

2.  **Handlers**: The entity that executes when an event is fired. A handler is typically an AI agent attached to a `/dev` device, allowing for complex, context-based decision-making. Standard skrips in `/sbin` or `/bin` could also serve as simpler, non-AI handlers.

3.  **Configuration**: A central configuration file, `/etc/daemons.conf`, maps events to their designated handlers. This provides a simple, clear way to enable, disable, and configure system daemons.

    Example `/etc/daemons.conf`:
    ```
    # event_name        handler_type    handler_specification
    POST_CODE_SAVE      device          /dev/google/gemini-2.5-pro
    USER_LOGIN          skrip           /sbin/daemons/login_briefing.sk
    ```

### Implementation Details

#### Kernel Modifications

The `IOSK` class in `src/iosk/kernel.py` would be augmented with a central event dispatcher:

`async def fire_event(self, io: Context, event_name: str, **context)`

This method would:
1.  Consult `/etc/daemons.conf` to find the registered handler for `event_name`.
2.  If a handler is found, prepare a prompt or arguments based on the `context` provided.
3.  Invoke the handler in-line with the original `io` context, pausing the current operation to await the daemon's completion.

#### In-line Execution

A key feature of this proposal is **in-line execution**. When a daemon is triggered, it doesn't run in the background. Instead, the originating process (e.g., an AI chat response) is paused. The daemon is invoked, and its actions and output are injected directly into the user's current session stream. This makes the daemon's work a seamless and immediate part of the user's interaction.

### Use Case: The Filesystem Organizer Daemon

This primary use case demonstrates the power of the proposed system.

**Problem:** When AI agents generate code, the `Engagement` class in `chat.py` currently saves these code blocks to a generic staging directory, `/var/code`. This requires a user or another agent to manually move the files to an appropriate project directory.

**Solution:** A daemon that listens for the `POST_CODE_SAVE` event to intelligently organize these files.

#### Step-by-Step Workflow

1.  **Code Generation**: A user, `alpha`, is interacting with the `openai` agent. `openai` provides a Python script to solve a problem, which is returned in a markdown code block.

2.  **Initial Save**: The `Engagement._handle_code_blocks_` method saves the script to a temporary path, e.g., `/var/code/openai-1-1.py`.

3.  **Event Firing**: Instead of printing `:: iosk auto-saved output to...`, the `_handle_code_blocks_` method now fires an event:
    ```python
    await io.os.fire_event(
        io,
        'POST_CODE_SAVE',
        files=['/var/code/openai-1-1.py'],
        history=io.session.getvalue() # Pass recent chat history
    )
    ```

4.  **Daemon Invocation**: The `fire_event` method in the kernel reads `/etc/daemons.conf` and identifies `/dev/google/gemini-2.5-pro` as the handler. The kernel then constructs a specialized prompt for this AI daemon.

5.  **Daemon Prompt**:
    ```
    SYSTEM TASK: FILE ORGANIZATION

    An agent has generated the files listed below. Your task is to analyze the provided chat context, determine the most appropriate location and name for these files, and issue the necessary `$ mv` or `$ cp` commands to organize them.

    CONTEXT (RECENT CHAT HISTORY):
    ---
    [alpha] >> $ ask openai "write me a python script to parse server logs from /var/log/nginx"
    :: Asking 'openai' via device '/dev/openai/gpt-4o'...
    -- Response from openai --
    Of course, here is a python script to get you started on parsing nginx logs.
    ```python
    import re
    # ... rest of python script ...
    ```
    ---

    FILES CREATED:
    - /var/code/openai-1-1.py

    INSTRUCTIONS:
    Your response must be ONLY the iosk command(s) required to move the file(s) to a logical project directory under the user's home. If no action is needed, respond with only "# no action".

    Example response:
    $ mv /var/code/openai-1-1.py /home/alpha/workspace/log-parser/parser.py
    ```

6.  **Daemon Response**: The `gemini-2.5-pro` agent receives this prompt, analyzes it, and returns the single command string:
    `$ mv /var/code/openai-1-1.py /home/alpha/workspace/log-parser/parser.py`

7.  **In-line Command Execution**: The kernel receives this string from the daemon. It then executes this command within `alpha`'s original `io` context using `await self.call(io, ...)`.

8.  **User Experience**: The user `alpha` sees the output from the `mv` command (`:: path moved`) directly in their session, immediately following the response from `openai`. The file is now correctly placed, and the entire organization happened automatically and transparently. The original chat flow then resumes.

### Benefits and Future Possibilities

-   **Intelligent Automation**: Automates tedious tasks like file management with context-aware AI, making the system smarter and more efficient.
-   **Seamless Integration**: The in-line execution model makes daemon actions feel like a natural part of the OS, not a disconnected background task.
-   **Extensibility**: This framework is highly extensible. New daemons could be created for a variety of tasks:
    -   A `USER_LOGIN` daemon to check for system messages, prepare a daily summary, or restore a user's previous session state.
    -   A `PRE_COMMAND_EXEC` daemon to act as a safety layer, warning users before executing potentially destructive commands like `rm -rf /`.
    -   A monitoring daemon to watch for specific patterns in `/var/log` and proactively alert users or other agents.
