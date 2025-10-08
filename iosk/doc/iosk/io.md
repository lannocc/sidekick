## Context Class Summary

The `Context` class manages the state and environment for a user's session or an individual process within the IOSK system. It is the central object for handling input/output streams, session history, environment variables, command aliases, and banked memory. Its design is crucial for supporting multi-user interactions, isolated process execution (e.g., for pipes), and advanced shell features like I/O redirection.

Here's a breakdown of the class and its methods:

**Class Attributes:**

*   `CID`: (int) A class-level counter used to assign unique IDs to `Context` instances upon creation.
*   `CHATTER`: (str) A class-level constant representing the base directory for "chatter" logs, which contain the raw I/O history of each context.
*   `CODE`: (str) A class-level constant for the directory used to store auto-saved code blocks.
*   `STAGE_PRE`: (int) Constant representing the "pre" stage, where output is captured to a string buffer, typically for preamble execution.
*   `STAGE_BANK`: (int) Constant representing the "bank" stage, where output is captured to a buffer for loading into core memory.
*   `STAGE_NORMAL`: (int) Constant representing the normal stage, where output is sent to its configured destination (console, file, or pipe).
*   `STAGE_POST`: (int) Constant representing the "post" stage, where output is captured to a string buffer, typically for postamble execution.

**Instance Attributes:**

*   `cid`: (int) A unique identifier for the `Context` instance, assigned from `Context.CID`.
*   `os`: (IOSK) An instance of the `IOSK` class, representing the underlying operating system kernel.
*   `dev`: (str) The virtual path of the device associated with this context (e.g., `/dev/console`, `/dev/google`).
*   `log`: (file handle or None) An optional file handle for structured logging of interactions.
*   `parent`: (Context or None) A reference to the parent `Context` if this is a forked context (e.g., for a command in a pipeline). `None` if it's a root context for a user session.
*   `chatter`: (file handle) A file handle for a raw chatter log file specific to this context.
*   `user`: (str or None) The username associated with this context.
*   `su`: (bool) `True` if the user has superuser privileges (i.e., is connected via the console or terminal device).
*   `base`: (bool) `True` if this is the root `Context` of a user's session, indicating it's the main process.
*   `bot`: (bool) `True` if the context represents a bot user, which affects I/O handling.
*   `paused`: (bool) `True` if the bot's AI engagement loop is paused, preventing it from making AI trips.
*   `login_time`: (datetime) The timestamp when the user's session was initiated.
*   `session`: (StringIO) A `StringIO` object that stores the entire chat history for a bot's session, used for constructing AI prompts.
*   `banks`: (dict) A dictionary representing the "core memory" available to the context, mapping bank identifiers (often file paths) to their content.
*   `env`: (dict) A dictionary storing environment variables specific to this context. Child contexts inherit and can override these.
*   `pwd`: (str or None) The current working directory of this context as a virtual path (e.g., `/home/user`).
*   `aliases`: (dict) A dictionary storing command aliases defined for this session (e.g., `{'ll': 'ls -l'}`).
*   `history`: (list) A list storing the command history for the current session.
*   `caching_token_total`, `full_token_total`, `initial_static_tokens`: (int) Attributes used for tracking estimated AI token usage throughout a session.
*   `preamble_cache`: (str) A cache for the output of the `/etc/chat/preamble` script to avoid re-executing it for every AI trip.
*   `stdin`: (StringIO or None) A stream representing the standard input for this context. If `None`, input is read from the device. If it's a `StringIO` object, commands will read from it. This is the core mechanism for **pipes**.
*   `stdout`: (File Handle or StringIO or None) A stream representing the standard output for this context. If `None`, output goes to the device. If it's a file handle or `StringIO`, all output is written to it. This is the core mechanism for **I/O redirection and pipes**.
*   `stage`: (int) The current processing stage, which controls where output is directed when `stdout` is not set.
*   `pre`, `post`, `banking`: Buffers (`StringIO` objects) used to capture output during the corresponding `stage`.

**Methods:**

*   `__init__(self, iosk_unix, dev_path, log_file=None)`:
    *   Constructor. Initializes the `Context` with the `IOSK` instance, device path, and optional log file.
    *   Assigns a unique `cid`, opens the `chatter` log, and initializes all instance attributes to their default states.

*   `fork(self)`:
    *   Creates a new child `Context` that inherits the state of the parent. This is essential for executing commands in a pipeline, where each command needs the parent's environment (`pwd`, `env`, etc.) but its own I/O streams.
    *   The child inherits `user`, `bot` status, `login_time`, `banks`, `pwd`, `env`, `aliases`, `stdin`, and `stdout`. Crucially, `env` and `aliases` are copied so child modifications do not affect the parent.

*   `environ(self)`:
    *   Retrieves the complete environment for this context by traversing up the parent chain and merging environment dictionaries. Child `env` settings take precedence over those in parent contexts.

*   `async print(self, text, indicator='=')`:
    *   A high-level method to print `text` to the context's output. It wraps `output()` and adds logging and a newline.

*   `async comment(self, text)`:
    *   Writes a comment to the `session` history if the context belongs to a bot. Used for internal annotation without sending output to a device.

*   `async input(self, prompt=None)`:
    *   Receives input from the user/device via `self.os.recv()`. It does not handle `stdin`; commands that read from stdin must do so explicitly.
    *   Logs the received data and appends it to the bot's `session` history.

*   `async output(self, text)`:
    *   The core method for sending output. It follows a strict order of precedence:
        1.  **`self.stdout`**: If `stdout` is set (to a file handle or `StringIO` buffer), all `text` is written directly to it. This is how I/O redirection (`>`) and pipes (`|`) are implemented.
        2.  **Staging**: If `stdout` is `None`, it then checks the current `self.stage`. If the stage is `STAGE_PRE`, `STAGE_BANK`, or `STAGE_POST`, it writes to the corresponding internal buffer (`self.pre`, etc.).
        3.  **Default**: If `stdout` is `None` and the stage is `STAGE_NORMAL`, it writes to the associated device (`self.os.send()`), the `chatter` log, the system log, and the bot's `session` history.

*   `async error(self, args)`:
    *   Prints an error message to the output using `print()` with an error indicator.

*   `stage_pre(self)`, `stage_bank(self, key)`, `stage_normal(self)`, `stage_post(self)`:
    *   These methods control the output staging system. They set the `stage` and manage the lifecycle of the `pre`, `post`, and `banking` buffers, allowing output to be captured and processed for specific purposes like populating banks or constructing AI prompts.

*   `_log_(self, indicator='=')`:
    *   A private helper method that writes a timestamped log entry to the `log` file.

**Capture Class:**

The `Capture` class is a simple utility for managing log files.

*   `logs` (dict): A class-level dictionary that caches opened file handles, keyed by their absolute path, to avoid reopening the same log file multiple times.

*   `log(cls, iosk, path, mkdirs=False)`:
    *   A class method that retrieves or creates a log file handle for a given path. It automatically appends the current date to the filename and creates parent directories if requested.

**Overall Purpose:**

The `Context` class is the backbone of user and process state management in IOSK. It provides an isolated environment for each session and command, manages I/O streams flexibly to support advanced shell features, handles logging, and maintains critical state like environment variables and banked memory. The staging system provides a mechanism for capturing and processing output for internal system tasks.

