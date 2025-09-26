## /bin Commands

These commands are generally available to users within the IOSK environment. Most `/bin` commands also accept `--help` as an option to display their specific help message.

*   **alias**: Manage IOSK command aliases.
    *   Usage: `$ alias` (list) or `$ alias NAME=VALUE` (define/update).
    *   Notes: `NAME=VALUE` defines a new alias or updates an existing one. NAME is the alias, VALUE is the command it expands to.
    *   Status: Working, but has known issues with variable expansion at definition time (not execution time) and nested quotes in alias definitions.
*   **ask**: Ask an AI user a question, with optional file/directory context.
    *   Usage: `$ ask [options] <user> <prompt>`
    *   Options: `-d <device>` (specify device model), `-f <file>` (attach file content), `-p <directory>` (package directory content), `-e <lang> <file>` (extract code block and save).
    *   Notes: Only one of -f or -p can be used at a time. The screenshot option (-s) is not available.
    *   Status: Broken (causes system to hang).
*   **attach**: Attach a device as a user.
    *   Usage: `$ attach <device> [handle]`
*   **bank**: Load a skrip account from `/bank` into core memory.
    *   Usage: `$ bank <bank> <account>`
    *   Status: Skipped (per project instructions).
*   **bankrupt**: Clear all loaded banks from core memory.
    *   Usage: `$ bankrupt`
    *   Status: Skipped (per project instructions).
*   **banks**: List memory accounts currently banked.
    *   Usage: `$ banks`
    *   Status: Skipped (related to banking commands).
*   **cat**: Display the contents of a file.
    *   Usage: `$ cat <filename>`
*   **cd**: Change the current working directory.
    *   Usage: `$ cd [directory]`
    *   Notes: If no directory is specified, it changes to the user's home directory (`/home/<user>`).
*   **cp**: Copy a file or directory.
    *   Usage: `$ cp <source> <destination>`
*   **date**: Display the current date and time.
    *   Usage: `$ date`
*   **describe**: Describe a file or directory.
    *   Usage: `$ describe <path>`
    *   Notes: Provides a concise summary: type, size, line/word counts for text, simple type heuristics.
*   **detach**: Detach a device user.
    *   Usage: `$ detach <handle>`
*   **diff**: Show differences between two text files.
    *   Usage: `$ diff [-u N] <file1> <file2>`
    *   Options: `-u N` (unified context lines, default 3).
    *   Notes: Files must be text; binary files are refused.
*   **echo**: Echo the given arguments.
    *   Usage: `$ echo [arguments]`
*   **export**: Set or display environment variables.
    *   Usage: `$ export [NAME=VALUE] ...`
    *   Notes: With no arguments, prints a list of all environment variables. Otherwise, sets each `NAME` to `VALUE`.
*   **get**: Get the contents of a file. (Alias for `cat`)
    *   Usage: `$ get <filename>`
    *   Notes: Behaves identically to `cat`.
*   **head**: Display the first N lines of a file.
    *   Usage: `$ head [-n <number>] <filename>`
    *   Options: `-n <number>` (specifies the number of lines to display, defaults to 10).
*   **help**: Display general help or command-specific help.
    *   Usage: `$ help` or `$ help <command>` or `$ help [-h|--help]`
    *   Notes: `help` displays the general IOSK help message. `help <command>` displays the help message for the specified command (equivalent to `<command> --help`).
*   **history**: Show recent command history for this session.
    *   Usage: `$ history [N]`
    *   Notes: `N` is the number of most recent commands to show (default 20). Only lines entered as commands (`$ ...`) are shown.
*   **ll**: Lists directory contents using the long listing format (alias for `ls -l`).
    *   Usage: `$ ll [path ...]`
    *   Notes: Provides one entry per line.
*   **ls**: List directory contents.
    *   Usage: `$ ls [options] [path ...]`
    *   Options: `-l` (long listing format), `-a` (list all entries, including those starting with '.').
    *   Notes: This command honors `.skignore` files in listed directories.
*   **mkdir**: Create a directory.
    *   Usage: `$ mkdir <directory>`
    *   Options: `-p` (allows parent directories to be created).
    *   Notes: Will error if the directory already exists or a path component is not a directory.
*   **mv**: Move or rename a file or directory.
    *   Usage: `$ mv <source> <destination>`
*   **patch**: Apply a diff to a file.
    *   Usage: `$ patch <targetfile> <patchfile>`
    *   Notes: This initial version can apply simple line-based patches.
*   **pwd**: Print the name of the current working directory.
    *   Usage: `$ pwd`
*   **rm**: Remove a file.
    *   Usage: `$ rm <filename>`
    *   Notes: This command does not support removing directories. Use `rmdir` for empty directories.
*   **rmdir**: Remove a directory.
    *   Usage: `$ rmdir <directory>`
    *   Notes: This command only removes empty directories.
*   **search**: Search for a term within text files.
    *   Usage: `$ search [-i] [-n] [-l] [-c] <term> [path ...]`
    *   Options: `-i` (case-insensitive), `-n` (show line numbers), `-l` (list filenames with matches), `-c` (print count of matches per file).
    *   Notes: No quoting is supported; `<term>` cannot contain spaces. If no paths are provided, defaults to `/home/<user>` if it exists; otherwise `/`.
*   **skrip**: Execute a skrip file or command string.
    *   Usage: `$ skrip <filename>` or `$ skrip -e <command>`
*   **status**: Displays system status information (date, user, users).
    *   Usage: `$ status`
*   **su**: Execute a command as another user.
    *   Usage: `$ su <user> <command> [args]`
    *   Notes: Requires super-user privileges.
*   **system**: Execute a command in the underlying host system.
    *   Usage: `$ system <command> [args...]`
    *   Notes: Executes directly on the host OS. Path-like arguments are sandboxed to host filesystem equivalents. Use with caution.
*   **tail**: Display the last N lines of a file.
    *   Usage: `$ tail [-n <number>] <filename>`
    *   Options: `-n <number>` (specifies the number of lines to display, defaults to 10).
*   **touch**: Create an empty file.
    *   Usage: `$ touch <filename>`
    *   Notes: Differs from standard UNIX `touch` as it errors if the file already exists, instead of updating its timestamp.
*   **tree**: List directory contents recursively in a tree-like format.
    *   Usage: `$ tree [options] [path ...]`
    *   Options: `-c` (count bytes and estimate tokens for the content).
    *   Notes: If no path is provided, uses the current directory.
*   **users**: List connected users.
    *   Usage: `$ users`
*   **wc**: Counts the number of lines, words, and characters in a file.
    *   Usage: `$ wc <filename>`
*   **welcome**: Displays a welcome message.
    *   Usage: `$ welcome`
*   **whoami**: Display the current username.
    *   Usage: `$ whoami`

## /sbin Commands

These commands are typically used for system administration tasks or internal system processes. Most `/sbin` commands also accept `--help` as an option to display their specific help message.

*   **init**: System initialization script.
    *   Usage: (Called automatically by the system)
    *   Notes: Sets up the initial `PATH` and performs other system startup tasks. Not intended for direct user invocation.
*   **shutdown**: Stop the IOSK system.
    *   Usage: `$ shutdown`
*   **postamble**: System script.
    *   Usage: (Called internally by AI engagement logic)
    *   Notes: Injects specific instructions or status updates into AI prompts. Not intended for direct user invocation.
*   **preamble**: System script.
    *   Usage: (Called internally by AI engagement logic)
    *   Notes: Injects core rules and context into AI prompts, defining the system's interactive behavior. Not intended for direct user invocation.

