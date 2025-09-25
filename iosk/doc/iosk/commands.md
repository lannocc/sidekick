## /bin Commands

These commands are generally available to users within the IOSK environment.

*   **alias**: Manage IOSK command aliases.
    Usage: `$ alias` (list) or `$ alias NAME=VALUE` (define/update).
*   **ask**: Asks an AI user a question, with optional file/directory context.
    Usage: `$ ask [options] <user> <prompt>`.
    Options: `-d <device>` (specify device model), `-f <file>` (attach file content), `-p <directory>` (package directory content), `-e <lang> <file>` (extract code block).
*   **attach**: Attach a user to a device.
    Usage: `$ attach <device> [handle]`.
*   **bank**: Load a skrip account from `/bank` into core memory.
    Usage: `$ bank <bank> <account>`.
*   **bankrupt**: Clear all loaded banks from core memory.
    Usage: `$ bankrupt`.
*   **banks**: Lists the names of memory accounts currently banked.
    Usage: `$ banks`.
*   **cat**: Display the contents of a file.
    Usage: `$ cat <filename>`.
*   **cp**: Copy a file or directory.
    Usage: `$ cp <source> <destination>`.
*   **date**: Display the current date and time.
    Usage: `$ date`.
*   **describe**: Describe a file or directory. Provides a concise summary: type, size, line/word counts for text, simple type heuristics.
    Usage: `$ describe <path>`.
*   **detach**: Detach a user from a device.
    Usage: `$ detach <handle>`.
*   **diff**: Show differences between two text files.
    Usage: `$ diff [-u N] <file1> <file2>`.
    Options: `-u N` (unified context lines).
*   **echo**: Echo the given arguments.
    Usage: `$ echo [arguments]`.
*   **export**: Set or display environment variables. With no arguments, prints a list of all environment variables. Otherwise, sets `NAME` to `VALUE`.
    Usage: `$ export [NAME=VALUE] ...`.
*   **get**: Get the contents of a file.
    Usage: `$ get <filename>`.
*   **head**: Display the first N lines of a file.
    Usage: `$ head [-n <number>] <filename>`.
*   **help**: Displays system-wide help information about available commands (this skrip).
    Usage: `$ help`.
*   **history**: Show recent command history for this session.
    Usage: `$ history [N]`.
    `N`: Number of most recent commands to show (default 20).
*   **ll**: Lists directory contents using the long listing format (alias for `ls -l`). Provides one entry per line.
    Usage: `$ ll [options] [path ...]`.
    Options: Inherited from `ls`.
*   **ls**: List directory contents.
    Usage: `$ ls [options] [path ...]`.
    Options: `-l` (long listing format), `-a` (list all entries, including those starting with '.').
*   **mkdir**: Create a directory.
    Usage: `$ mkdir [-p] <directory>`.
    `-p`: Allows parent directories to be created.
*   **mv**: Move or rename a file or directory.
    Usage: `$ mv <source> <destination>`.
*   **patch**: Apply a diff to a file. Note: This initial version can apply simple line-based patches.
    Usage: `$ patch <targetfile> <patchfile>`.
*   **rm**: Remove a file.
    Usage: `$ rm <filename>`.
*   **rmdir**: Remove a directory.
    Usage: `$ rmdir <directory>`.
*   **search**: Search for a term within text files.
    Usage: `$ search [-i] [-n] [-l] [-c] <term> [path ...]`.
    Options: `-i` (case-insensitive), `-n` (show line numbers), `-l` (list filenames), `-c` (count matches per file).
*   **skrip**: Execute a skrip file or command string.
    Usage: `$ skrip <filename>` or `$ skrip -e <command>`.
*   **status**: Displays system status information (date, user, users).
    Usage: `$ status`.
*   **su**: Execute a command as another user.
    Usage: `$ su <user> <command> [args]`.
*   **tail**: Display the last N lines of a file.
    Usage: `$ tail [-n <number>] <filename>`.
*   **touch**: Create an empty file.
    Usage: `$ touch <filename>`.
*   **tree**: List directory contents recursively in a tree-like format.
    Usage: `$ tree [options] [path ...]`.
    Options: `-c` (count bytes and estimate tokens).
*   **users**: List connected users.
    Usage: `$ users`.
*   **wc**: Counts the number of lines, words, and characters in a file.
    Usage: `$ wc <filename>`.
*   **welcome**: Displays a welcome message.
    Usage: `$ welcome`.
*   **whoami**: Display the current username.
    Usage: `$ whoami`.

Most `/bin` commands also accept `--help` as an option to display their specific help message.

## /sbin Commands

These commands are typically used for system administration tasks.

*   **init**: Starts the IOSK system.
    Usage: `$ init`.
*   **shutdown**: Stops the IOSK system.
    Usage: `$ shutdown`.

Most `/sbin` commands also accept `--help` as an option to display their specific help message.
