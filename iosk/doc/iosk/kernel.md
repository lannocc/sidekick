## IOSK Class Summary

The `IOSK` class (found in kernel.py) represents the core operating system kernel, managing the system's lifecycle, user sessions, command execution, file system operations, and device interactions. It acts as the central coordinator for all activities within the system.

**Class Attributes:**

*   `BOOT`: (int) The current boot number of the system. Initialized to 0 and incremented on each boot.
*   `CONSOLE_DEV`: (str) The path to the system's console device (`/dev/console`).
*   `BOOT_COUNT`: (str) The path to the file storing the boot count (`/var/cache/boot`).
*   `INIT_SCRIPT`: (str) The path to the system initialization script (`/sbin/init`).
*   `SYSTEM_LOG`: (str) The path to the system log file (`/var/log/system`).
*   `USER_LOG`: (str) The path to the directory storing user-specific log files (`/var/log/user`).
*   `SKRC`: (str) The path to the system-wide startup script for user sessions (`/etc/skrc`).

**Instance Attributes:**

*   `root`: (str) The root directory path of the IOSK file system.
*   `started`: (datetime) The datetime object indicating when the IOSK instance started (or `None` if not yet started).
*   `ready`: (asyncio.Event) An asyncio Event that is set when the IOSK instance is ready to accept user logins and commands.
*   `halt`: (asyncio.Event) An asyncio Event that is set when a shutdown signal is received, triggering the shutdown sequence.
*   `system`: (Context) The system-level `Context` instance representing the system environment. This is used for system-level logging, error reporting, and command execution.
*   `users`: (dict) A dictionary storing currently logged-in users. The keys are user handles (usernames), and the values are `Context` instances associated with each user.
*   `chat`: (obj) A chat interface (instance of AIMessenger of chat.py), used for communicating between users and bots. Can be `None` if not available.
*   `parser`: (CommandLineParser) An instance of `CommandLineParser` responsible for handling command line tokenization and variable expansion.

**Methods:**

*   `__init__(self, root)`:
    *   Constructor. Initializes the `IOSK` instance with the given `root` directory.
    *   Sets `started` to `None`, creates asyncio Events for `ready` and `halt`, and initializes the `system` and `users` attributes.
    *   Initializes `self.parser` with a reference to itself, to enable robust command-line parsing.

*   `async start(self)`:
    *   Starts the IOSK system. This involves the following steps:
        *   Prints "IOSK is starting...".
        *   Validates that `self.root` is a directory.
        *   Reads the boot count from `self.BOOT_COUNT` and increments it.
        *   Creates directories for chatter (`/var/cache/chatter/<boot_number>`) and code (`/var/code`) if they don't exist, and ensures they are directories.
        *   Writes the updated boot count to `self.BOOT_COUNT`.
        *   Creates the `self.system` Context and redirects output to the system log.
        *   Executes the system initialization script (`self.INIT_SCRIPT`).
        *   Prints "IOSK has started."
    *   Sets the `ready` event if everything starts successfully. If an error occurs, it prints an error message and halts the startup process.

*   `async run(self)`:
    *   Runs the IOSK system. This function performs these actions:
        *   Waits for the `ready` event to be set (i.e., waits for the system to be initialized).
        *   Prints "IOSK is ready."
        *   Waits for the `halt` event to be set, indicating a shutdown signal.
        *   Prints "IOSK shutdown signal received...".
        *   Logs out all currently logged-in users.
        *   Prints "IOSK system halted.".
        *   Sets `self.system` to `None`.

*   `async login(self, user, device=None, interactive: bool = True, connect=None, io_callback=None)`:
    *   Logs in a user and creates a `Context` for the user.
    *   Waits for the `ready` event.
    *   Validates that the user is not already logged in and that the username is not reserved.
    *   Creates a forked `Context` from the `self.system` Context.
    *   Sets up user-specific logging, the device, and the username within the `Context`.
    *   Automatically creates the user's home directory (`/home/<user>`) on the host filesystem if it does not exist, and logs this action.
    *   Sets the user's current working directory (`io.pwd`) to `/home/<user>`.
    *   Executes the system-wide `skrc` script (`/etc/skrc`).
    *   Executes the user-specific `skrc` script (`/home/<user>/.skrc`) if it exists.
    *   If `interactive` is `True`, starts an interactive shell for the user.
    *   Returns the created `Context`.

*   `async interactive(self, io)`:
    *   Provides an interactive shell for the given `Context`.
    *   Continuously prompts the user for input, executes commands, and handles chat messages.
    *   Supports exiting the shell with `$ exit`.
    *   Passes the raw command line string (after the `$ ` prefix) directly to `self.call` for advanced parsing and execution.
    *   Adds non-empty commands to `io.history`.
    *   Sends other lines to the chat (if a chat interface is available) or prints them to the console.
    *   Handles `EOFError` for clean exit.

*   `async logout(self, io: Context, disconnect=None)`:
    *   Logs out a user and removes their `Context`.
    *   Validates that the user is currently logged in.
    *   Prints a logout message to the system log.
    *   Sends a disconnect message to the chat (if available) or prints it to the console.
    *   Removes the user's `Context` from the `self.users` dictionary.

*   `async call(self, io: Context, args: str)`:
    *   **Completely overhauled** to provide robust command parsing. It takes a raw command string (`args`) and performs the following pipeline:
        1.  **Alias Resolution**: Checks if the first word of the command (`cmd_candidate`) matches an alias in `io.aliases`. If so, it expands the alias value into the `args` string *before* further parsing.
        2.  **Advanced Parsing and Tokenization**: The (potentially alias-expanded) command string is passed to `self.parser.parse_and_tokenize()`. This method (located in `src/iosk/parser.py`) is responsible for:
            *   **Command Substitution**: Handles `...` and `$(...)` syntax.
            *   **Variable Expansion**: Expands environment variables using `$VAR` and `${VAR}` syntax, substituting them with values from `io.environ()`.
            *   **Tokenization**: Uses `shlex.split()` to robustly tokenize the fully expanded string into a list of arguments (`argv`), correctly handling spaces and quotes.
        3.  **Command Lookup**: Determines the executable path by:
            *   Checking if `cmd` (the first token in `argv`) is an absolute path or explicit relative path (e.g., `/bin/ls`, `./script`).
            *   If `cmd` is a bare name (e.g., `ls`), it searches directories listed in the `PATH` environment variable (`io.environ().get('PATH')`). If `PATH` is not set, it defaults to searching in `/bin`.
            *   For each potential path, it first attempts to load it as a Python module (`.py` file with an `iocall` function) by creating a module spec without full import.
            *   If not a Python module, it attempts to find it as a regular executable file (e.g., a `.skrip` script).
        4.  **Execution**:
            *   If resolved as a Python module, it imports the module (using `self.pymod`) and calls its `iocall(io, cmd_args)` method, passing `cmd_args` as a `list` of strings (excluding the command name itself).
            *   If resolved as a script, it calls `self.exec(io, resolved_internal_path, cmd_args)`.
    *   Handles exceptions during command execution, logging them with `io.error` and `traceback.print_exc()`. Returns `True` on success, `False` on failure.

*   `async exec(self, io: Context, path: str, argv: list = None)`:
    *   Executes a script at the given `path`. This method expects `path` to be an absolute virtual path within the sandboxed filesystem (e.g., `/bin/myscript`). It does not search the `PATH` environment variable for the executable itself.
    *   Accepts `argv` as a `list` of strings (defaulting to empty).
    *   Reads the shebang line. If it specifies an interpreter (e.g., `#!/bin/skrip`), it constructs a new command string using `shlex.join()` to invoke the interpreter (e.g., `skrip /path/to/script.skrip arg1 arg2`) and recursively calls `self.call()` to execute it.
    *   Logs an error if there's no shebang or a bad shebang. Returns `True` on success, `False` on failure.

*   `async exists(self, io: Context, path: str)`:
    *   Tests whether a file exists.
    *   Uses `self.box(path, io_context=io)` to resolve the path on the host filesystem.
    *   Optionally checks for a special `proc.exists.<name>` Python module for custom existence logic, but primarily checks `os.path.exists()`.

*   `async create(self, io: Context, path: str)`:
    *   Creates a new (empty) file.
    *   Uses `self.box(path, io_context=io)` for path resolution.
    *   If the file already exists, it is considered a success (idempotent) and returns `True`.
    *   Creates the file on the host filesystem. Returns `True` on success.

*   `async copy(self, io: Context, from_path: str, to_path: str)`:
    *   Copies a file from `from_path` to `to_path`.
    *   Uses `self.box()` with `io_context=io` for both paths.
    *   Errors if `from_path` does not exist. Uses `shutil.copy()`. Returns `True` on success, `False` on failure.

*   `async move(self, io: Context, from_path: str, to_path: str)`:
    *   Moves a file or directory from `from_path` to `to_path`.
    *   Uses `self.box()` with `io_context=io` for both paths.
    *   Errors if `from_path` does not exist. Uses `shutil.move()` (which handles both files and directories). Returns `True` on success, `False` on failure.

*   `async remove(self, io: Context, path: str)`:
    *   Removes a file at `path`.
    *   Uses `self.box(path, io_context=io)` for path resolution.
    *   Errors if `path` does not exist. Returns `True` on success, `False` on failure.

*   `async create_dir(self, io: Context, path: str, parents=False)`:
    *   Creates a new directory at `path`.
    *   Uses `self.box(path, io_context=io)` for path resolution.
    *   If `parents` is `True`, creates parent directories as needed.
    *   Errors if `path` already exists. Returns `True` on success, `False` on failure.

*   `async remove_dir(self, io: Context, path: str)`:
    *   Removes an empty directory at `path`.
    *   Uses `self.box(path, io_context=io)` for path resolution.
    *   Errors if `path` does not exist. Returns `True` on success, `False` on failure (e.g., directory not empty).

*   `async get(self, io: Context, path: str)`:
    *   Gets the text contents of a file.
    *   Uses `self.box(path, io_context=io)` for path resolution.
    *   Errors and returns `None` if the path is not found, not a file, or if it's detected as a binary file.
    *   Reads the file with UTF-8 encoding.

*   `async send(self, io: Context, dev: str, data)`:
    *   Sends data to a device (e.g., `/dev/console`).
    *   Resolves the device path to a Python module (`dev.<device_name>`).
    *   Calls the `iosend(io, data)` function within that module.
    *   Logs errors, including `traceback.print_exc()`. Returns `True` on success, `False` on failure.

*   `async recv(self, io: Context, dev: str)`:
    *   Receives data from a device.
    *   Resolves the device path to a Python module (`dev.<device_name>`).
    *   Calls the `iorecv(io)` function within that module.
    *   Logs errors, including `traceback.print_exc()`. Returns the received data (or `None` on error or no data).

*   `box(self, virtual_path_input: str, io_context=None) -> str`:
    *   Sandboxes a given `virtual_path_input` to its equivalent absolute path on the host filesystem.
    *   **Enhanced Functionality**:
        1.  If `io_context` is provided and `virtual_path_input` is a relative path, it first resolves the path relative to `io_context.pwd` (the current working directory of the user context).
        2.  Normalizes the resulting virtual path (e.g., resolves `.` and `..`, collapses multiple slashes).
        3.  Ensures the normalized path is absolute within the virtual filesystem (prepends `/` if necessary).
        4.  Combines this normalized virtual path (relative to the virtual root) with `self.root` (the actual host root of the IOSK filesystem) to get the final host path.
        5.  Returns the absolute host filesystem path.

*   `pymod(self, modname, path)`:
    *   Imports a Python module from the given `path` with the specified `modname`.
    *   It internally prefixes `modname` with `sk.iosk.`
    *   Handles adding the `.py` extension if missing.
    *   Uses `importlib.util.spec_from_file_location` and `spec.loader.exec_module` for robust module loading.
    *   Stores the module in `sys.modules` for subsequent access.
    *   Includes a fallback to `importlib.import_module` and handles potential `ModuleNotFoundError`. Returns the loaded module object or `None` on failure.

In essence, the `IOSK` class provides a virtualized operating system environment, enabling the execution of scripts and Python commands, management of user sessions, and interaction with virtual devices, all within a sandboxed environment. The command parsing and file system interaction mechanisms have been significantly enhanced for robustness and `PATH` awareness, now leveraging a dedicated `CommandLineParser`.
