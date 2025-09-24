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
2.  If a handler is found, prepare a prompt or arguments based on the `context` provided. For AI agent handlers, this prompt is constructed by combining standardized `preamble` and `postamble` files (e.g., from `/etc/daemons/`) with the dynamic context of the event. This standardizes how different parts of the system (chat, daemons, the `ask` command) build their prompts.
3.  Invoke the handler in-line with the original `io` context, pausing the current operation to await the daemon's completion.

#### Prompt Standardization

A key part of the system's design is standardizing how prompts are constructed for AI agents. Rather than hardcoding prompts, the system uses a file-based approach within the `/etc/` directory. For example:
-   Standard chat interactions use `/etc/chat/preamble` and `/etc/chat/postamble`.
-   The `ask` command would use files in `/etc/ask/`.
-   Daemon events, as described here, use files located in `/etc/daemons/`.

This allows system administrators to easily customize and tune the behavior of AI interactions across the entire OS.

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

4.  **Daemon Invocation**: The `fire_event` method in the kernel reads `/etc/daemons.conf` and identifies `/dev/google/gemini-2.5-pro` as the handler.

5.  **Daemon Prompt**: The kernel constructs the prompt by combining `/etc/daemons/preamble`, the dynamic event context, and `/etc/daemons/postamble`. For instance, `/etc/daemons/preamble` might contain the static instructions, and the kernel injects the context in between:
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


### A Simpler Approach: Daemons as UNIX Pipes

In keeping with the UNIX philosophy of "do one thing and do it well," the proposed daemon system could be simplified. Instead of a specialized `fire_event` kernel mechanism, we can leverage the well-understood concept of standard input/output and pipes.

In this model:

1.  **Events as Text Streams**: When an event occurs, the kernel serializes the event context (e.g., filenames, user, chat history) into a simple text format (like plain text or JSON) and pipes it to the standard input of the handler process.
2.  **Handlers as Filters**: A daemon handler becomes a standard executable (a skrip, a Python program, etc.) that reads from `stdin`, performs its logic, and writes any resulting commands to `stdout`. It acts as a filter, transforming event data into executable commands.
3.  **Simple Execution**: The kernel's only job is to execute the handler specified in `/etc/daemons.conf`, pipe the context to it, and then execute whatever commands the handler prints to its standard output.

An example workflow for the `POST_CODE_SAVE` event would be:

```bash
# Kernel internally prepares the context and pipes it to the handler
$ echo "/var/code/openai-1-1.py" | /sbin/daemons/organizer.sk
```

The `/sbin/daemons/organizer.sk` handler would read the filename from stdin, decide on a new location, and print the command:

```bash
# Output from organizer.sk
$ mv /var/code/openai-1-1.py /home/alpha/workspace/log-parser/parser.py
```

The kernel then executes this output.

**Benefits of this approach:**

*   **Simplicity**: It removes the need for a complex event API within the kernel, relying instead on standard process management and I/O redirection.
*   **Composability**: Any program that can read from stdin and write to stdout can be a daemon handler, not just specialized AI agents. Handlers can be chained together using standard shell pipes.
*   **Testability**: Daemon handlers can be easily tested from the command line without needing the full IOSK kernel, simply by piping test data to them: `cat test_event.txt | /sbin/daemons/organizer.sk`.
*   **Flexibility**: This aligns perfectly with the "everything is a file" philosophy, treating events as streams of data to be processed by simple, focused tools.
