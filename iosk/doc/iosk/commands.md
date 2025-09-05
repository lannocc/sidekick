## /bin Commands

These commands are generally available to users within the IOSK environment.

*   **attach**:  Connects a user to a device. Takes a device name and optional handle. Usage: `$ attach <device> [handle]`
*   **bank**: Loads a skrip account from `/bank` into core memory. Requires a bank and account name.  Usage: `$ bank <bank> <account>`
*   **bankrupt**: Clears all loaded banks from core memory. Usage: `$ bankrupt`
*   **banks**: Lists currently loaded banks in core memory. Usage: `$ banks`
*   **cat**: Displays the contents of a file. Usage: `$ cat <filename>`
*   **cp**: Copies a file from source to destination. Usage: `$ cp <src> <dst>`
*   **date**: Displays the current date and time. Usage: `$ date`
*   **detach**: Disconnects a user from a device. Requires a handle/username. Usage: `$ detach <handle>`
*   **echo**:  Prints the given arguments. Usage: `$ echo <text>`
*   **get**: Outputs file contents without formatting/prefixing. Usage: `$ get <filename>`
*   **head**: Displays the first N lines of a file. Usage: `$ head [-n <number>] <filename>`
*   **help**:  Displays help information about available commands. Usage: `$ help`
*   **ll**: Lists directory contents using the long listing format (alias for `ls -l`). Usage: `$ ll [path]`
*   **ls**: Lists directory contents. Takes an optional directory path. Usage: `$ ls [path]`
*   **mkdir**: Creates a new directory.  Supports creating parent directories with the `-p` flag. Usage: `$ mkdir [-p] <directory>`
*   **mv**: Moves a file or directory from source to destination. Usage: `$ mv <src> <dst>`
*   **rm**: Removes a file. Usage: `$ rm <path>`
*   **rmdir**: Removes a directory. Usage: `$ rmdir <directory>`
*   **skrip**: Executes a skrip file. Usage: `$ skrip <path>`
    *   `-e`: executes a string as a skrip line.
*   **status**: Displays system status information (date, user, users). Usage: `$ status`
*   **su**: Execute a command as another user. Usage: `$ su <user> <command> [args]`
*   **tail**: Displays the last N lines of a file. Usage: `$ tail [-n <number>] <filename>`
*   **touch**: Creates a new, empty file. Usage: `$ touch <filename>`
*   **tree**: Lists directory contents recursively in a tree-like format. Usage: `$ tree [path ...]`
*   **users**: Lists currently connected users. Usage: `$ users`
*   **whoami**: Displays the current username. Usage: `$ whoami`

## /sbin Commands

These commands are typically used for system administration tasks.

*   **init**: Starts the IOSK system. Usage: `$ init`
*   **shutdown**: Stops the IOSK system. Usage: `$ shutdown`

