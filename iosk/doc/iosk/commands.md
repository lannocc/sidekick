## /bin Commands

These commands are generally available to users within the IOSK environment. Most `/bin` commands also accept `--help` as an option to display their specific help message.

*   **alias**: Manage IOSK command aliases.
    *   Usage: `$ alias` (list) or `$ alias NAME=VALUE` (define/update).
    *   Notes: `NAME=VALUE` defines a new alias or updates an existing one. NAME is the alias, VALUE is the command it expands to. Variables within an alias definition (e.g., `$PATH`) are expanded *during the alias definition itself*, not during alias execution. The parser struggles with nested quotes in alias definitions.
    *   Status: Working (with caveats - alias quoting and expansion issues exist but are not a high priority to resolve immediately given the parser proposal's status).
*   **ask**: Ask an AI user a question, with optional file/directory context.
    *   Usage: `$ ask [options] <prompt>` or `... | ask [options]`
    *   Notes: If `<prompt>` is not provided as an argument, it is read from standard input.
    *   Options: `-q`, `--quiet` (quiet mode); `-f <file>` (attach file content, can be specified multiple times); `-p <directory>` (package directory content, can be specified multiple times); `-e <lang> <file>` (extract first markdown code block of `<lang>` and save); `-1` (use model gemini-2.0-flash-lite); `-2` (use model gemini-2.5-flash, default); `-3` (use model gemini-2.5-pro).
    *   Status: Working.
*   **attach**: Attach a device as a user.
    *   Usage: `$ attach <device> [handle]`
    *   Status: Working.
*   **bank**: Load a skrip into core memory banks.
    *   Usage: `$ bank <path components...>` or `... | bank`
    *   Notes: Loads the content of a file into memory. If the file has a shebang (e.g., `#!/bin/skrip`), it is executed and its output is captured. Otherwise, the raw file content is loaded directly. The path can be absolute (e.g., `/etc/skrc`), relative to the CWD (e.g., `./myskrip`), or relative to `/bank` (e.g., `role devops`). If input is piped, the content is loaded directly without execution.
    *   Status: Working.
*   **bankrupt**: Clear all loaded banks from core memory.
    *   Usage: `$ bankrupt`
    *   Status: Working.
*   **banks**: List memory accounts currently banked.
    *   Usage: `$ banks`
    *   Status: Working.
*   **cat**: Display the contents of a file.
    *   Usage: `$ cat <filename>`
    *   Status: Working.
*   **cd**: Change the current working directory.
    *   Usage: `$ cd [directory]`
    *   Notes: If no directory is specified, it changes to the user's home directory (`/home/<user>`).
    *   Status: Working.
*   **clear**: Clear the session history for bots or the screen for console users.
    *   Usage: `$ clear`
    *   Notes: For bot users, clears the entire chat session history, leaving only the `clear` command itself. For interactive console users, clears the screen.
    *   Status: Working.
*   **cp**: Copy a file or directory.
    *   Usage: `$ cp <source> <destination>`
    *   Status: Working (file to file copy, file to existing directory copy).
*   **date**: Display the current date and time.
    *   Usage: `$ date` or `$ date <format>`
    *   Notes: The format string should start with a `+` (e.g., `"+%Y%m%d_%H%M%S"`), using Python's `datetime strftime` format codes.
    *   Status: Working.
*   **describe**: Describe a file or directory.
    *   Usage: `$ describe <path>`
    *   Notes: Provides a concise summary: type, size, line/word counts for text, simple type heuristics.
    *   Status: Working.
*   **detach**: Detach a device user.
    *   Usage: `$ detach <handle>`
    *   Status: Working.
*   **diff**: Show differences between two text files.
    *   Usage: `$ diff [-u N] <file1> <file2>`
    *   Options: `-u N` (unified context lines, default 3).
    *   Notes: Files must be text; binary files are refused.
    *   Status: Working.
*   **echo**: Echo the given arguments.
    *   Usage: `$ echo [arguments]`
    *   Status: Working.
*   **export**: Set or display environment variables.
    *   Usage: `$ export [NAME=VALUE] ...`
    *   Notes: With no arguments, prints a list of all environment variables. Otherwise, sets each `NAME` to `VALUE`.
    *   Status: Working.
*   **get**: Get the contents of a file. (Alias for `cat`)
    *   Usage: `$ get <filename>`
    *   Notes: Behaves identically to `cat`.
    *   Status: Working.
*   **grep**: Search for a regular expression PATTERN in each FILE or standard input.
    *   Usage: `$ grep [OPTIONS] PATTERN [FILE...]`
    *   Options: `-i`, `--ignore-case` (ignore case distinctions); `-v`, `--invert-match` (select non-matching lines); `-n`, `--line-number` (prefix with line number); `-l`, `--files-with-matches` (print filenames only); `-c`, `--count` (print count of matching lines); `-r`, `-R`, `--recursive` (read all files under each directory, recursively).
    *   Status: Working.
*   **head**: Display the first N lines of a file or stdin.
    *   Usage: `$ head [-n <number>] [filename]`
    *   Options: `-n <number>` (specifies the number of lines to display, defaults to 10). If filename is omitted, reads from stdin.
    *   Status: Working.
*   **help**: Display general help or command-specific help.
    *   Usage: `$ help` or `$ help <command>` or `$ help [-h|--help]`
    *   Notes: `help` displays the general IOSK help message. `help <command>` displays the help message for the specified command (equivalent to `<command> --help`).
    *   Status: Fully functional.
*   **history**: Show recent command history for this session.
    *   Usage: `$ history [N]`
    *   Notes: `N` is the number of most recent commands to show. If omitted, the entire session history is displayed. Only lines entered as commands (`$ ...`) are shown.
    *   Status: Working as expected.
*   **ll**: Lists directory contents using the long listing format (alias for `ls -l`).
    *   Usage: `$ ll [path ...]`
    *   Notes: Provides one entry per line.
    *   Status: Working (as an alias).
*   **ls**: List directory contents.
    *   Usage: `$ ls [options] [path ...]`
    *   Options: `-l` (long listing format), `-a` (list all entries, including those starting with '.').
    *   Notes: This command honors `.skignore` files in listed directories.
    *   Status: Working.
*   **mkdir**: Create a directory.
    *   Usage: `$ mkdir <directory>...` or `$ mkdir -p <directory>...`
    *   Options: `-p` (allows parent directories to be created).
    *   Notes: Multiple directories can be specified. Will error if the directory already exists or a path component is not a directory.
    *   Status: Working.
*   **mv**: Move or rename a file or directory.
    *   Usage: `$ mv <source> <destination>`
    *   Notes: If `DESTINATION` is an existing directory, `SOURCE` is moved into it. If `DESTINATION` is a filename, `SOURCE` is renamed to `DESTINATION`. Errors if `SOURCE` does not exist or if `DESTINATION` is a non-existent directory.
    *   Status: Working.
*   **patch**: Apply a diff to a file.
    *   Usage: `$ patch <targetfile> <patchfile>`
    *   Notes: This initial version can apply simple line-based patches.
    *   Status: Working.
*   **pause**: Pause a bot user's AI engagement.
    *   Usage: `$ pause [username]`
    *   Notes: Pauses the AI engagement for the specified bot user. The bot will stop making AI trips and will not receive new chat messages until unpaused. If no username is provided, it attempts to pause the current user. The console user cannot be paused.
    *   Status: Working.
*   **pwd**: Print the name of the current working directory.
    *   Usage: `$ pwd`
    *   Status: Working.
*   **reattach**: Reattach a user to a different device.
    *   Usage: `$ reattach <device> [user]`
    *   Notes: `<device>` is the name of the device (e.g., 'dummy', 'google', 'openai/gpt-4o'), corresponding to a path under `/dev/`. `[user]` is the username to reattach; if omitted, defaults to the current user.
    *   Status: Working.
*   **rm**: Remove files.
    *   Usage: `$ rm <filename>...`
    *   Notes: This command does not support removing directories. Use `rmdir` for empty directories. Multiple files can be specified.
    *   Status: Working for files, but explicitly fails for directories (which is expected for a basic `rm` command).
*   **rmdir**: Remove one or more directories.
    *   Usage: `$ rmdir <directory>...`
    *   Notes: This command only removes empty directories. Multiple directories can be specified.
    *   Status: Working.
*   **search**: Search for a term within text files or stdin.
    *   Usage: `$ search [-i] [-n] [-l] [-c] <term> [path ...]`
    *   Options: `-i` (case-insensitive), `-n` (show line numbers), `-l` (list filenames with matches), `-c` (print count of matches per file).
    *   Notes: If no paths are provided, reads from standard input. If stdin is empty, defaults to `/home/<user>` if it exists; otherwise `/`.
    *   Status: Working.
*   **send**: Send file contents or piped data as a message to the chat (to all users).
    *   Usage: `$ send <file>...` or `... | send`
    *   Notes: Reads content from one or more files, or from standard input, and broadcasts it as a single raw text message. The sender receives a confirmation.
    *   Status: Working.
*   **skrip**: Execute a skrip file or command string.
    *   Usage: `$ skrip <filename>` or `$ skrip -e <command>`
    *   Status: Working.
*   **status**: Displays system status information (date, user, users).
    *   Usage: `$ status`
    *   Status: Working.
*   **su**: Execute a command as another user, with optional piped input.
    *   Usage: `$ su <user> <command> [args...]` or `... | su <user> <command> [args...]`
    *   Notes: Requires super-user privileges. When standard input is piped to `su`, it is passed as standard input to the executed command.
    *   Status: Working (functionality for super-users is assumed based on the explicit error for non-super-users).
*   **system**: Execute a command in the underlying host system.
    *   Usage: `$ system <command> [args...]`
    *   Notes: Executes directly on the host OS. Path-like arguments are sandboxed to host filesystem equivalents. Use with caution.
    *   Status: Working.
*   **tail**: Display the last N lines of a file or stdin.
    *   Usage: `$ tail [-n <number>] [filename]`
    *   Options: `-n <number>` (specifies the number of lines to display, defaults to 10). If filename is omitted, reads from stdin.
    *   Status: Working.
*   **ticket**: View ticket details from the database.
    *   Usage: `$ ticket <ticket-number>`
    *   Notes: `<ticket-number>` is the ID of the ticket to view (e.g., 123 or T123).
    *   Status: Working.
*   **tokens**: Calculate the total bytes and estimate tokens for the current session context.
    *   Usage: `$ tokens`
    *   Notes: This command assembles the full context that would be sent to an AI, including the preamble, banked memory, chat history, and postamble, then reports the size of that context. It also displays session-long running totals.
    *   Status: Working.
*   **touch**: Create an empty file.
    *   Usage: `$ touch <filename>`
    *   Notes: Differs from standard UNIX `touch` as it errors if the file already exists, instead of updating its timestamp.
    *   Status: Working as a file creation utility, but non-standard behavior for existing files.
*   **tree**: List directory contents recursively in a tree-like format.
    *   Usage: `$ tree [options] [path ...]`
    *   Options: `-c` (count bytes and estimate tokens for the content).
    *   Notes: Some files and folders are hidden (this command honors `.skignore` files). If no path is provided, uses the current directory.
    *   Status: Working.
*   **unpause**: Unpause a bot user's AI engagement.
    *   Usage: `$ unpause <username>`
    *   Notes: Resumes the AI engagement for a previously paused bot user. Must be run by another user, as a paused user cannot execute commands.
    *   Status: Working.
*   **users**: List connected users.
    *   Usage: `$ users`
    *   Status: Working.
*   **wc**: Counts the number of lines, words, and characters in a file or stdin.
    *   Usage: `$ wc [file]`
    *   Notes: If no file is specified, reads from standard input.
    *   Status: Working.
*   **welcome**: Displays a welcome message.
    *   Usage: `$ welcome`
    *   Status: Working.
*   **whatami**: Display the name of the current device.
    *   Usage: `$ whatami`
    *   Notes: Does not accept arguments. Strips the `/dev/` prefix from the device path for a cleaner display.
    *   Status: Working.
*   **which**: Locate a command executable in the PATH.
    *   Usage: `$ which <command>`
    *   Notes: Searches the directories specified in the `PATH` environment variable for the given command name. Prioritizes Python (`.py`) module files over script files without an extension if both exist, matching the kernel's command resolution logic.
    *   Status: Working.
*   **whoami**: Display the current username.
    *   Usage: `$ whoami`
    *   Status: Working.
*   **xargs**: Build and execute command lines from standard input.
    *   Usage: `... | xargs [options] [command [initial-arguments]]`
    *   Options: `-n <max-args>` (use at most `max-args` arguments per command line); `-I <replace-str>` (replace occurrences of `replace-str` in initial arguments); `--help` (display help).
    *   Notes: Reads items from standard input, delimited by spaces or newlines. If no command is given, `echo` is used by default. Options `-I` and `-n` are mutually exclusive. Other standard `xargs` options (like `-0`, `-L`, `-t`, `-r`, `-p`) are supported internally by `shlex` but some output behaviors (`stderr` visibility, interactive prompts with `-p`) may be limited in a non-interactive chat environment.
    *   Status: Working (with noted behaviors for non-interactive output).

## /sbin Commands

These commands are typically used for system administration tasks. Most `/sbin` commands also accept `--help` as an option to display their specific help message.

*   **init**: System initialization script.
    *   Usage: (Called automatically by the system)
    *   Notes: Sets up the initial `PATH` and performs other system startup tasks. Not intended for direct user invocation.
    *   Status: Assumed Working. Needs NO further testing.
*   **shutdown**: Stop the IOSK system.
    *   Usage: `$ shutdown`
    *   Notes: Initiates the shutdown sequence for the IOSK system. This command signals the underlying operating system to halt the system.
    *   Status: Assumed working. No further testing required as execution interrupts the running system.
