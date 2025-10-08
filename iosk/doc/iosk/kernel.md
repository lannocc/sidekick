## IOSK Class Summary

The `IOSK` class (found in `src/iosk/kernel.py`) represents the core operating system kernel, managing the system's lifecycle, user sessions, command execution, process management, API rate limiting, tracing, file system operations, and device interactions. It acts as the central coordinator for all activities within the system.

**Class Attributes:**

*   `BOOT`: (int) The current boot number of the system. Initialized to 0 and incremented on each boot.
*   `CONSOLE_DEV`: (str) The path to the system's console device (`/dev/console`).
*   `BOOT_COUNT`: (str) The path to the file storing the boot count (`/var/cache/boot`).
*   `INIT_SCRIPT`: (str) The path to the system initialization script (`/sbin/init`).
*   `SYSTEM_LOG`: (str) The path to the system log file (`/var/log/system`).
*   `USER_LOG`: (str) The path to the directory storing user-specific log files (`/var/log/user`).
*   `SKRC`: (str) The path to the system-wide startup script for user sessions (`/etc/skrc`).
*   `SKEL_SKRC`: (str) The path to the skeleton startup script that is copied to a new user's home directory (`/etc/skel/skrc`).

**Instance Attributes:**

*   `root`: (str) The root directory path of the IOSK file system on the host.
*   `started`: (datetime) The datetime object indicating when the IOSK instance started.
*   `ready`: (asyncio.Event) An asyncio Event that is set when the IOSK instance is ready to accept user logins and commands.
*   `halt`: (asyncio.Event) An asyncio Event that is set when a shutdown signal is received, triggering the shutdown sequence.
*   `system`: (Context) The system-level `Context` instance representing the system environment.
*   `users`: (dict) A dictionary storing currently logged-in users, mapping usernames to their `Context` instances.
*   `chat`: (AIMessenger) The chat interface, used for communicating between users and bots.
*   `parser`: (CommandLineParser) An instance of `CommandLineParser` responsible for handling command line tokenization, variable expansion, and command substitution.
*   `pipeline_executor`: (CommandPipelineExecutor) An instance of `CommandPipelineExecutor` responsible for orchestrating the entire command execution flow, including alias resolution, parsing, handling pipes and I/O redirection, and process management.
*   `process_table`: (dict) An in-memory dictionary mapping Process IDs (PIDs) to `Process` objects for all currently running commands.
*   `next_pid`: (int) A counter for assigning the next unique Process ID.
*   `device_clients`: (dict) A cache for initialized AI client instances, keyed by their virtual device path (e.g., `/dev/google/gemini-2.5-pro`).
*   `trace_states`: (dict) A dictionary holding the on/off state for all named trace points (e.g., `'trip': True`).
*   `device_trip_counters`: (dict) A dictionary storing per-device trip counters for unique trace log naming.
*   `device_tpm_trackers`: (dict) A dictionary for tracking token usage per minute for each AI device to manage API rate limits.
*   `device_cooldowns`: (dict) A dictionary of `asyncio.Event`s used to manage API rate limit cooldowns for each device.

**Methods:**

*   `__init__(self, root)`:
    *   Constructor. Initializes the `IOSK` instance with the `root` directory.
    *   Initializes all instance attributes, including creating asyncio Events, setting up the system `Context`, and instantiating the `CommandLineParser` and `CommandPipelineExecutor`.

*   `start(self)`:
    *   Starts the IOSK system. This involves:
        *   Incrementing the boot count.
        *   Creating necessary directories like `/var/cache/chatter`, `/var/code`, and `/var/log/trip` if they don't exist.
        *   Creating the `system` Context and redirecting its output to the system log.
        *   Executing the system initialization script (`/sbin/init`).
    *   Sets the `ready` event upon successful startup.

*   `run(self)`:
    *   Main system loop. It waits for the `ready` event, then waits for the `halt` event (shutdown signal).
    *   Upon shutdown, it logs out all users and cleans up the system state.

### Token Rate Limiting

*   `_get_current_tpm(self, device_path)`:
    *   Calculates the current tokens-per-minute (TPM) for a given device by summing token counts from the last 60 seconds and pruning old entries from the tracker.
*   `async enforce_cooldown(self, device_path, delay_seconds)`:
    *   Triggers a mandatory, system-wide cooldown for a specific device, typically after a `429` rate limit error. It blocks new requests to that device for the specified duration.
*   `async await_device_readiness(self, user, device_path, tokens_in_prompt)`:
    *   Central entry point for all AI trips. It first waits if the device is in a reactive cooldown period. Then, it proactively checks if the new request will exceed the TPM quota and sleeps briefly if necessary to prevent hitting the rate limit.

### User Lifecycle

*   `async login(self, user, device=None, ...)`:
    *   Logs in a user and creates a `Context` for their session.
    *   **Home Directory Auto-Creation**: Automatically creates the user's home directory (`/home/<user>`) on the host filesystem if it does not exist.
    *   **Skeleton Configuration**: If a home directory is newly created, it copies a default startup script from `/etc/skel/skrc` to the user's `~/.skrc`.
    *   **Startup Scripts**: Executes the system-wide `/etc/skrc` script, followed by the user-specific `~/.skrc` script if it exists, to configure the user's environment.
    *   Returns the created `Context`.

*   `async interactive(self, io)`:
    *   Provides an interactive shell for the given `Context`. It reads user input, identifies command lines (prefixed with `$ `), and passes the raw command string to `self.call` for execution. Other lines are sent to the chat.

*   `async logout(self, io: Context, ...)`:
    *   Logs out a user and removes their `Context` from the system.

### Command Execution

*   `async call(self, io: Context, args: str)`:
    *   The primary entry point for all command executions. It delegates the entire execution pipeline to the `CommandPipelineExecutor`.
    *   The pipeline handles alias resolution, robust parsing (including command substitution and variable expansion), I/O redirection (`>`, `>>`), pipes (`|`), and process management.

*   `async exec(self, io: Context, path: str, argv: list = None)`:
    *   Executes a script at a given absolute virtual `path`. This method is called by the pipeline executor after a command has been resolved to a script file.
    *   It reads the shebang line (e.g., `#!/bin/skrip`). If an interpreter is specified, it constructs a new command (e.g., `skrip /path/to/script arg1`) and recursively calls `self.call` to execute it, ensuring the interpreter runs through the same robust pipeline.

### File & Device Operations

*   `async exists(self, io: Context, path: str)`:
    *   Tests whether a path exists. Enhanced to check for physical files/directories, corresponding Python module files (`.py`), and built-in Python modules that don't have a physical file in the sandbox (e.g., `/dev/google`).
*   `async create`, `copy`, `move`, `remove`, `create_dir`, `remove_dir`:
    *   Standard file system operations. The `copy`, `move`, and `create_dir` methods are enhanced to automatically create parent directories as needed, improving robustness.
*   `async get(self, io: Context, path: str)`:
    *   Gets the text contents of a file, refusing to read binary files.
*   `async send(self, io: Context, dev: str, data)` / `async recv(self, io: Context, dev: str)`:
    *   Sends data to or receives data from a virtual device by invoking the `iosend` or `iorecv` function within the corresponding device's Python module.
*   `async get_device_client(self, io: Context, dev_virtual_path: str)`:
    *   Gets a cached AI client instance for a device (e.g., for Google Gemini or OpenAI). If no cached instance exists, it calls the `get_client` factory function in the device's module to create a new one, then caches and returns it. This centralizes client management.

### Tracing

*   `async is_trace_active(self, trace_name: str)`:
    *   Checks if a specific trace point (e.g., `trip`) is currently enabled.
*   `async log_trip_trace(self, io: Context, prompt: str, reply: str)`:
    *   Logs the details of an AI interaction. It always calculates token counts for TPM tracking. If the `trip` trace is active, it writes the full prompt, the raw reply, and a token/byte count summary to uniquely named files in `/var/log/trip/`.

### Utility

*   `box(self, virtual_path_input: str, io_context=None)`:
    *   Sandboxes a given virtual path to its equivalent absolute path on the host filesystem. It now correctly resolves relative paths (like `./script` or `file.txt`) against the user's current working directory (`io_context.pwd`).
*   `pymod(self, modname, path)`:
    *   Imports a Python module from a given path within the sandbox, using a specified module name. This is the core mechanism for loading commands and device drivers.

