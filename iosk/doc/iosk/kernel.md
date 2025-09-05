## IOSK Class Summary

The `IOSK` class (found in kernel.py) represents the core operating system kernel, managing the system's lifecycle, user sessions, command execution, file system operations, and device interactions.  It acts as the central coordinator for all activities within the system.

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

**Methods:**

*   `__init__(self, root)`:
    *   Initializes the IOSK instance with the given `root` directory.
    *   Sets `started` to `None`, creates asyncio Events for `ready` and `halt`, and initializes the `system` and `users` attributes.

*   `async start(self)`:
    *   Starts the IOSK system.  This involves the following steps:
        *   Prints "IOSK is starting...".
        *   Validates that `self.root` is a directory.
        *   Reads the boot count from `self.BOOT_COUNT` and increments it.
        *   Creates directories for chatter and code if they don't exist.
        *   Writes the updated boot count to `self.BOOT_COUNT`.
        *   Creates the `self.system` Context and redirects output to the system log.
        *   Executes the system initialization script (`self.INIT_SCRIPT`).
        *   Prints "IOSK has started."
    *   Sets the `ready` event if everything starts successfully. If an error occurs, it prints an error message and halts the startup process.

*   `async run(self)`:
    *   Runs the IOSK system.  This function performs these actions:
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
    *   Executes `skrc` init scripts.
    *   Starts an interactive shell (if `interactive` is `True`).
    *   Returns the created `Context`.

*   `async interactive(self, io)`:
    *   Provides an interactive shell for the given `Context`.
    *   Continuously prompts the user for input, executes commands, and handles chat messages.
    *   Supports exiting the shell with `$ exit`.
    *   Supports commands starting with `$ ` which executes shell commands.
    *   Supports comments starting with `#`.
    *   Sends other lines to the chat (if a chat interface is available) or prints them to the console.
    *   Handles `EOFError` for clean exit.

*   `async logout(self, io: Context, disconnect=None)`:
    *   Logs out a user and removes their `Context`.
    *   Validates that the user is currently logged in.
    *   Prints a logout message to the system log.
    *   Sends a disconnect message to the chat (if available) or prints it to the console.
    *   Removes the user's `Context` from the `self.users` dictionary.

*   `async call(self, io: Context, args)`:
    *   Interprets arguments and invokes a command.
    *   Parses the command name and arguments.
    *   Checks if a Python module exists for the command.
    *   If a Python module exists, it calls the `iocall` function within the module.
    *   Otherwise, it executes the command as a file.
    *   Handles exceptions during command execution.

*   `async exec(self, io: Context, path: str, args: str = None)`:
    *   Executes a script at the given path.
    *   Checks if the file exists.
    *   Reads the shebang line (if any).
    *   If a shebang line exists, it calls the corresponding interpreter.
    *   Otherwise, it logs an error.

*   `async exists(self, io: Context, path: str)`:
    *   Tests whether a file exists.
    *   Checks if a python module named 'proc.exists' exists.
    *   If it doesn't, checks if the file exists on disk.

*   `async create(self, io: Context, path: str)`:
    *   Creates a new (empty) file.

*   `async copy(self, io: Context, from_path: str, to_path: str)`:
    *   Copies a file from one path to another.

*   `async move(self, io: Context, from_path: str, to_path: str)`:
    *   Moves a file or directory from one path to another.

*   `async remove(self, io: Context, path: str)`:
    *   Removes a file.

*   `async create_dir(self, io: Context, path: str, parents=False)`:
    *   Creates a new directory.
    *   `parents`: if `True`, creates parent directories as needed.

*   `async remove_dir(self, io: Context, path: str)`:
    *   Removes a directory.

*   `async get(self, io: Context, path: str)`:
    *   Gets the contents of a file.

*   `async send(self, io: Context, dev: str, data)`:
    *   Sends data to a device.
    *   Checks if a Python module exists for the device.
    *   If a Python module exists, it calls the `iosend` function within the module.
    *   Otherwise, it executes the device as a file.

*   `async recv(self, io: Context, dev: str)`:
    *   Receives data from a device.
    *   Checks if a Python module exists for the device.
    *   If a Python module exists, it calls the `iorecv` function within the module.
    *   Otherwise, it executes the device as a file.

*   `box(self, file)`:
    *   Sandboxes a file path by ensuring it's within the root directory.
    *   Removes leading slashes, `./`, and `../` from the path.
    *   Joins the resulting path with the root directory (`self.root`).

*   `pymod(self, modname, path)`:
    *   Imports a Python module at the given path as the given module name.
    *   Attempts to import the module using `importlib.util.spec_from_file_location`.
    *   If that fails, it tries `importlib.import_module`.

In essence, the `IOSK` class provides a virtualized operating system environment, enabling the execution of scripts, management of user sessions, and interaction with virtual devices, all within a sandboxed environment.



