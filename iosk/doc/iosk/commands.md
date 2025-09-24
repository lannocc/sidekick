## /bin Commands

These commands are generally available to users within the IOSK environment.

*   **ask**: Asks an AI agent a question. Usage: `$ ask <agent> "<prompt>"`
*   **attach**: Connects a user to a device. Takes a device name and optional handle. Usage: `$ attach <device> [handle]`
*   **bank**: Loads a skrip account from `/bank` into core memory. Requires a bank and account name. Usage: `$ bank <bank> <account>`
*   **bankrupt**: Clears all loaded banks from core memory. Usage: `$ bankrupt`
*   **banks**: Lists currently loaded banks in core memory. Usage: `$ banks`
*   **cat**: Displays the contents of a file. Usage: `$ cat <filename>`
*   **cp**: Copies a file from source to destination. Usage: `$ cp <src> <dst>`
*   **date**: Displays the current date and time. Usage: `$ date`
*   **describe**: Provides a concise summary of a file or directory. Usage: `$ describe <path>`
*   **detach**: Disconnects a user from a device. Requires a handle/username. Usage: `$ detach <handle>`
*   **diff**: Compares two files and shows their differences. Usage: `$ diff <file1> <file2>`
*   **echo**: Prints the given arguments. Usage: `$ echo <text>`
*   **export**: Displays environment variables. Usage: `$ export`
*   **get**: Outputs file contents without formatting/prefixing. Usage: `$ get <filename>`
*   **head**: Displays the first N lines of a file. Usage: `$ head [-n <number>] <filename>`
*   **help**: Displays help information about available commands. Usage: `$ help`
*   **history**: Displays the command history for the current session. Usage: `$ history [N]`
*   **ll**: Lists directory contents using the long listing format (alias for `ls -l`). Usage: `$ ll [path]`
*   **ls**: Lists directory contents. Takes an optional directory path. Usage: `$ ls [path]`
*   **mkdir**: Creates a new directory. Supports creating parent directories with the `-p` flag. Usage: `$ mkdir [-p] <directory>`
*   **mv**: Moves a file or directory from source to destination. Usage: `$ mv <src> <dst>`
*   **patch**: Applies a diff file to a target file. Usage: `$ patch <target_file> <patch_file>`
*   **rm**: Removes a file. Usage: `$ rm <path>`
*   **rmdir**: Removes a directory. Usage: `$ rmdir <directory>`
*   **search**: Searches for a specified term within text files. Usage: `$ search <term> [path ...]`
*   **skrip**: Executes a skrip file. Usage: `$ skrip <path>`
    *   `-e`: executes a string as a skrip line.
*   **status**: Displays system status information (date, user, users). Usage: `$ status`
*   **su**: Execute a command as another user. Usage: `$ su <user> <command> [args]`
*   **tail**: Displays the last N lines of a file. Usage: `$ tail [-n <number>] <filename>`
*   **touch**: Creates a new, empty file. Usage: `$ touch <filename>`
*   **tree**: Lists directory contents recursively in a tree-like format. Usage: `$ tree [path ...]`
*   **users**: Lists currently connected users. Usage: `$ users`
*   **wc**: Counts the number of lines, words, and characters in a file. Usage: `$ wc <filename>`
*   **welcome**: Displays a welcome message. Usage: `$ welcome`
*   **whoami**: Displays the current username. Usage: `$ whoami`

## /sbin Commands

These commands are typically used for system administration tasks.

*   **init**: Starts the IOSK system. Usage: `$ init`
*   **shutdown**: Stops the IOSK system. Usage: `$ shutdown`

