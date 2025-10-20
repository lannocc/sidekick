## /bin Commands

These commands are generally available to users within the IOSK environment. Most `/bin` commands also accept `--help` as an option to display their specific help message.

*   **alias**: Manage IOSK command aliases.
    *   Usage: `$ alias` (list) or `$ alias NAME=VALUE` (define/update).
    *   Notes: `NAME=VALUE` defines a new alias or updates an existing one. NAME is the alias, VALUE is the command it expands to. Variables within an alias definition (e.g., `$PATH`) are expanded *during the alias definition itself*, not during alias execution. The parser struggles with nested quotes in alias definitions.
    *   Status: Working (with caveats - alias quoting and variable expansion issues exist but are not a high priority to resolve immediately given the parser status).
*   **ask**: Ask an AI a question, with optional file/directory context.
    *   Usage: `$ ask [options] <prompt>` or `... | ask [options]`
    *   Options: `-h, --help` (Displays this help message.); `-q, --quiet` (Quiet mode. Only print the final AI response.); `-f <file>` (Attach the contents of the specified file to the prompt. Can be specified multiple times.); `-p <directory>` (Package and attach the contents of the specified directory. Can be specified multiple times.); `-e <lang> <file>` (Extract the first markdown code block of `<lang>` from the response and save it to `<file>.`); `-1` (Use model: gemini-2.0-flash-lite.); `-2` (Use model: gemini-2.5-flash (default).); `-3` (Use model: gemini-2.5-pro.).
    *   Notes: If `<prompt>` is not provided as an argument, it is read from standard input.
    *   Status: Working.
*   **attach**: Attach a device as a user.
    *   Usage: `$ attach <device> [handle]`
    *   Notes: `handle` defaults to `device` if not provided and is normalized to replace '/' with '-'. Requires an active chat system and will bring the attached user into the current active room.
    *   Status: Working.
*   **bank**: Load a file's content into core memory banks.
    *   Usage: `$ bank <path components...>` or `... | bank`
    *   Notes: If the file has a shebang (e.g., `#!/bin/skrip`), it is executed and its output is captured. Otherwise, the raw file content is loaded directly. The path can be absolute (e.g., `/etc/skrc`), relative to the CWD (e.g., `./myskrip`), or relative to `/bank` (e.g., `role devops`). If a given path is not found and it does not already end with .md, the command will also try to find the file by appending a .md extension. If input is piped, the content is loaded directly into memory without being executed as a skrip.
    *   Status: Working.
*   **bankrupt**: Clear all loaded banks from core memory.
    *   Usage: `$ bankrupt`
    *   Notes: Removes all entries from `io.banks`.
    *   Status: Working.
*   **banks**: List memory accounts currently banked.
    *   Usage: `$ banks`
    *   Notes: Prints the virtual paths (keys) of all loaded memory banks.
    *   Status: Working.
*   **cat**: Display the contents of a file.
    *   Usage: `$ cat <filename>`
    *   Notes: Requires a filename argument.
    *   Status: Working.
*   **cd**: Change the current working directory.
    *   Usage: `$ cd [directory]`
    *   Notes: If no directory is specified, it changes to the user's home directory (`/home/<user>`).
    *   Status: Working.
*   **clear**: Clear the session history for bots or the screen for console users.
    *   Usage: `$ clear`
    *   Notes: For bot users, this command clears the entire chat session history, leaving only the `clear` command itself as the first and only entry. For interactive console/terminal users, this command clears the screen using ANSI escape sequences.
    *   Status: Working.
*   **clroom**: Close the active chat room.
    *   Usage: `$ clroom`
    *   Notes: Closes the single active chat room on the local system. This command can typically only be run by the room's owner or a superuser.
    *   Status: Working.
*   **cp**: Copy a file or directory.
    *   Usage: `$ cp <source> <destination>`
    *   Notes: Handles file-to-file copy and file-to-existing-directory copy. Errors if source does not exist.
    *   Status: Working.
*   **date**: Display the current date and time, with optional formatting.
    *   Usage: `$ date` or `$ date <format>`
    *   Notes: The format string should start with a `+` (e.g., `"+%Y%m%d_%H%M%S"`), using Python's `datetime strftime` format codes.
    *   Status: Working.
*   **describe**: Describe a file or directory.
    *   Usage: `$ describe <path>`
    *   Notes: Provides a concise summary: type, size, line/word counts for text, simple type heuristics.
    *   Status: Working.
*   **detach**: Detach a device user.
    *   Usage: `$ detach <handle>`
    *   Notes: Requires a username/handle argument. The target user must be currently attached.
    *   Status: Working.
*   **diff**: Show differences between two text files.
    *   Usage: `$ diff [-u N] <file1> <file2>`
    *   Options: `-u N` (unified context lines, default 3).
    *   Notes: Files must be text; binary files are refused by the system.
    *   Status: Working.
*   **echo**: Echo the given arguments.
    *   Usage: `$ echo [arguments]`
    *   Notes: Prints arguments as a single space-separated string.
    *   Status: Working.
*   **export**: Set or display environment variables.
    *   Usage: `$ export [NAME=VALUE] ...`
    *   Notes: With no arguments, prints a list of all environment variables. Otherwise, sets each `NAME` to `VALUE`. Values are stored after stripping a single layer of quotes.
    *   Status: Working.
*   **get**: Get the contents of a file.
    *   Usage: `$ get <filename>`
    *   Notes: Behaves identically to `cat`. Requires a filename argument.
    *   Status: Working.
*   **grep**: Search for a regular expression PATTERN in each FILE or standard input.
    *   Usage: `$ grep [OPTIONS] PATTERN [FILE...]`
    *   Options: `-i, --ignore-case` (ignore case distinctions); `-v, --invert-match` (select non-matching lines); `-n, --line-number` (prefix with line number); `-l, --files-with-matches` (print filenames only); `-c, --count` (print count of matching lines); `-r, -R, --recursive` (read all files under each directory, recursively).
    *   Notes: If no files are given, reads from standard input.
    *   Status: Working.
*   **head**: Display the first N lines of a file or stdin.
    *   Usage: `$ head [-n <number>] [filename]`
    *   Options: `-n <number>` (specifies the number of lines to display, defaults to 10).
    *   Notes: If filename is omitted, reads from stdin.
    *   Status: Working.
*   **help**: Display general help or command-specific help.
    *   Usage: `$ help` or `$ help <command>` or `$ help [-h|--help]`
    *   Notes: `help` displays the general IOSK help message. `help <command>` displays the help message for the specified command (equivalent to `<command> --help`).
    *   Status: Fully functional.
*   **history**: Show recent command history for this session.
    *   Usage: `$ history [N]`
    *   Notes: `N` is the number of most recent commands to show. If omitted, the entire session history is displayed. Only lines entered as commands (`$ ...`) are shown.
    *   Status: Working.
*   **hostname**: Display or set the system's hostname.
    *   Usage: `$ hostname` or `$ hostname <new-hostname>`
    *   Notes: `hostname` prints the current hostname. `hostname <new-hostname>` sets the system's hostname to the new value, updating both `/etc/hostname` and the runtime configuration.
    *   Status: Working.
*   **kill**: Terminate a running process.
    *   Usage: `$ kill <pid>`
    *   Notes: `<pid>` is the Process ID of the process to terminate. Use `ps` to find PIDs.
    *   Status: Working.
*   **ll**: Lists directory contents using the long listing format (alias for `ls -l`).
    *   Usage: `$ ll [path ...]`
    *   Notes: Provides one entry per line with detailed information. This command is an alias for `ls -l`.
    *   Status: Working (as an alias).
*   **login**: Log in as a different user.
    *   Usage: `$ login <username>`
    *   Notes: Logs out the current session and starts a new session for the specified user on the same device. Useful for switching users without restarting the system.
    *   Status: Working.
*   **ls**: List directory contents.
    *   Usage: `$ ls [options] [path ...]`
    *   Options: `-l` (long listing format), `-a` (list all entries, including those starting with '.').
    *   Notes: Hides system dotfiles (`.`, `..`, `__pycache__`, `~`-ending files) by default unless `-a` is used.
    *   Status: Working.
*   **mesh**: Connect to other IOSK systems or view the current network mesh.
    *   Usage: `$ mesh` or `$ mesh <host[:port]>`
    *   Notes: `mesh` lists all connected peer systems. `mesh <host[:port]>` establishes an outbound connection to another IOSK system's listener service (defaults to port 4209).
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
*   **on**: Execute a command on a remote, connected host.
    *   Usage: `$ on <host> <command...>`
    *   Notes: `<host>` is the hostname of a connected peer system. `<command...>` is the command and its arguments to execute remotely. Output is streamed back and displayed locally.
    *   Status: Working.
*   **patch**: Apply a diff to a file.
    *   Usage: `$ patch <targetfile> <patchfile>`
    *   Notes: This initial version can apply simple line-based diffs (unified diff format) to a target file.
    *   Status: Working.
*   **pause**: Pause a bot user's AI engagement.
    *   Usage: `$ pause [username]`
    *   Notes: Pauses the AI engagement for the specified bot user. If no username, pauses current user. Console user cannot be paused.
    *   Status: Working.
*   **port**: Controls the network listener service.
    *   Usage: `$ port`, `$ port on [port_num]`, `$ port off`
    *   Notes: `port` displays status. `port on` starts the listener (default 4209). `port off` stops it.
    *   Status: Working.
*   **ps**: List currently running processes.
    *   Usage: `$ ps`
    *   Notes: Displays information about active processes, including their PID, user, running time, and the command string.
    *   Status: Working.
*   **pwd**: Print the name of the current working directory.
    *   Usage: `$ pwd`
    *   Notes: Does not accept arguments.
    *   Status: Working.
*   **reattach**: Reattach a user to a different device.
    *   Usage: `$ reattach <device> [user]`
    *   Notes: `<device>` is the device name (e.g., 'dummy', 'google', 'openai/gpt-4'). `[user]` is the username (defaults to current). Console device targets (`/dev/console`) allow swapping if already occupied.
    *   Status: Working.
*   **replace**: Replaces occurrences of a string in a file with another string.
    *   Usage: `replace <filename> <old_string> <new_string>`
    *   Notes: `<filename>` is the path to the file to modify. `<old_string>` is the string to search for. `<new_string>` is the string to replace with.
    *   Status: Working.
*   **reset**: Reset a user's session to a clean state.
    *   Usage: `$ reset [username]`
    *   Notes: Clears session history, command history, loaded banks, environment variables, aliases, and resets the current working directory to the user's home. Then, it re-runs the system-wide `/etc/skrc` and the user's `~/.skrc` file, simulating a fresh login. If no username is provided, it resets the current user's session. Only superusers can reset the session of another user.
    *   Status: Working.
*   **rm**: Remove files.
    *   Usage: `$ rm <filename>...`
    *   Notes: This command does not support removing directories. Use `rmdir` for empty directories. Multiple files can be specified.
    *   Status: Working for files, but explicitly fails for directories (which is expected for a basic `rm` command).
*   **rmdir**: Remove one or more directories.
    *   Usage: `$ rmdir <directory>...`
    *   Notes: This command only removes empty directories. Multiple directories can be specified.
    *   Status: Working.
*   **room**: Opens a new local chat room.
    *   Usage: `$ room [room_name]`
    *   Notes: Opens a new chat room on the local system. Defaults to 'iosk'. Only one room can be active at a time.
    *   Status: Working.
*   **rooms**: List all rooms created on the local system.
    *   Usage: `$ rooms [-s | --simple]`
    *   Notes: Lists all rooms created on the local system. By default, lists in verbose, multi-column format showing ROOM and TOPIC. The currently active room is indicated with a leading tilde (~), followed by the count of active users in parentheses, e.g., `~iosk(2)`. The `-s, --simple` option uses a compact, single-column format.
    *   Status: Working.
*   **search**: Search for a term within text files or stdin.
    *   Usage: `$ search [-i] [-n] [-l] [-c] <term> [path ...]`
    *   Options: `-i` (case-insensitive), `-n` (show line numbers), `-l` (list filenames with matches), `-c` (print count of matches per file).
    *   Notes: If no paths are provided, reads from standard input. If stdin is empty, defaults to `/home/<user>` if it exists; otherwise `/`.
    *   Status: Working.
*   **send**: Send file contents or piped data as a message to the chat.
    *   Usage: `$ send [-u <user>]... <file>...` or `... | send [-u <user>]...`
    *   Options: `-u <user>` (Send a direct message to a specific user. This option can be used multiple times to specify multiple recipients in `user` or `user.host` format.).
    *   Notes: Reads the contents of one or more files, or reads from standard input, and sends the result as a raw text message. By default, the message is broadcast to other users in the current chat.
    *   Status: Working.
*   **skrip**: Execute a skrip file or command.
    *   Usage: `$ skrip <filename>` or `$ skrip -e <command>` or `$ skrip -s <filename>`
    *   Notes: `<filename>` (default mode): Lines starting with '$ ' are commands; other lines are printed. `-e <command>`: Execute the given command string in default mode. `-s <filename>`: Execute the given file in "pure shell mode". All non-comment lines are treated as commands and do not need a '$ ' prefix.
    *   Status: Working.
*   **sleep**: Pause execution for a specified amount of time.
    *   Usage: `$ sleep <duration>...`
    *   Notes: Pauses for an amount of time specified by the sum of the values of the command line arguments. Each argument is a number followed by an optional unit (s, m, h, d). Default unit is seconds. A direct message sent to a sleeping user will interrupt the sleep.
    *   Status: Working.
*   **status**: Displays system status information (date, user, users).
    *   Usage: `$ status`
    *   Notes: A skrip that calls `date`, `whoami`, and `users`.
    *   Status: Working.
*   **su**: Execute a command as another user, with optional piped input.
    *   Usage: `$ su <user> <command> [args...]` or `... | su <user> <command> [args...]`
    *   Notes: When standard input is piped to `su`, it is passed as standard input to the executed command. Requires super-user privileges.
    *   Status: Working.
*   **system**: Execute a command in the underlying host system.
    *   Usage: `$ system <command> [args...]`
    *   Notes: Executes directly on the host OS. Path-like arguments are sandboxed to host filesystem equivalents. Use with caution.
    *   Status: Working.
*   **tail**: Display the last N lines of a file or stdin.
    *   Usage: `$ tail [-n <number>] [filename]`
    *   Options: `-n <number>` (specifies the number of lines to display, defaults to 10).
    *   Notes: If filename is omitted, reads from stdin.
    *   Status: Working.
*   **ticket**: View ticket details from the database.
    *   Usage: `$ ticket <ticket-number>`
    *   Notes: `<ticket-number>` is the ID of the ticket to view (e.g., 123 or T123). Requires database configuration in `/etc/`.
    *   Status: Working.
*   **tokens**: Calculate the total bytes and estimate tokens for the current session context.
    *   Usage: `$ tokens`
    *   Notes: Assembles the full context that would be sent to an AI (preamble, banked memory, chat history, postamble) and reports its size, along with session-long running totals.
    *   Status: Working.
*   **top**: Provide a single, non-interactive snapshot of system activity.
    *   Usage: `$ top`
    *   Notes: Displays a summary of system status and a list of running processes, sorted by runtime in descending order. This is a one-shot command and does not update in real-time.
    *   Status: Working.
*   **topic**: View or set the topic for the current chat room.
    *   Usage: `$ topic` or `$ topic <new topic>`
    *   Notes: `topic` displays the current room's topic. `<new topic>` sets the room's topic. Only room owner or superuser can set topic.
    *   Status: Working.
*   **touch**: Create an empty file.
    *   Usage: `$ touch <filename>`
    *   Notes: Creates a new, empty file. If the file already exists, the command errors, unlike standard UNIX `touch` which updates the timestamp.
    *   Status: Working as a file creation utility, with non-standard behavior for existing files.
*   **trace**: Manage the IOSK system-wide tracing facility.
    *   Usage: `$ trace`, `$ trace on|off`, `$ trace <name> on|off`
    *   Notes: `trace` lists all trace points and their state. `trace on|off` enables/disables all traces. `trace <name> on|off` enables/disables a specific trace point.
    *   Status: Working.
*   **tree**: List directory contents recursively in a tree-like format.
    *   Usage: `$ tree [options] [path ...]`
    *   Options: `-c` (count bytes and estimate tokens for the content); `-d` (list directories only).
    *   Notes: Some files and folders are hidden (this command honors `.skignore` files). If no path is provided, uses the current directory.
    *   Status: Working.
*   **unmesh**: Disconnect from one or more peer IOSK systems.
    *   Usage: `$ unmesh [host...]`
    *   Notes: `unmesh` (no arguments) disconnects from all peers. `unmesh <host...>` disconnects from specified peers.
    *   Status: Working.
*   **unpause**: Unpause a bot user's AI engagement.
    *   Usage: `$ unpause <username>`
    *   Notes: Resumes the AI engagement for a previously paused bot user. Must be run by another user, as a paused user cannot execute commands.
    *   Status: Working.
*   **users**: List connected users.
    *   Usage: `$ users`
    *   Notes: Prints the usernames of all currently connected users and a count.
    *   Status: Working.
*   **ver**: Display the current version of SideKick/IOSK.
    *   Usage: `$ ver`
    *   Notes: Does not accept arguments. `--help` displays its own help message.
    *   Status: Working.
*   **watch**: Execute a command repeatedly, displaying its output (console only).
    *   Usage: `$ watch [options] <command>`
    *   Options: `-n <seconds>` (update interval, default 2.0s), `-c` (enable color).
    *   Notes: This command is only available to users on a console device. To exit, press Ctrl-C or use `kill`.
    *   Status: Working.
*   **wc**: Counts the number of lines, words, and characters in a file or stdin.
    *   Usage: `$ wc [file]`
    *   Notes: If no file is specified, reads from standard input.
    *   Status: Working.
*   **welcome**: Displays a welcome message.
    *   Usage: `$ welcome`
    *   Notes: A simple skrip that prints "Welcome to IOSK!".
    *   Status: Working.
*   **where**: Display a list of all known users across the network mesh.
    *   Usage: `$ where [-s | --simple]`
    *   Notes: By default, displays a verbose, multi-column format showing USER, HOST, and ROOM. The user running the command is indicated with a leading tilde (~). For the local host, the HOST column is blank. The `-s, --simple` option uses a compact, single-column format: 'user.host/room'.
    *   Status: Working.
*   **whereami**: Display the configured hostname and active room of the local IOSK system.
    *   Usage: `$ whereami`
    *   Notes: Displays the unique hostname of the local IOSK system. If a chat room is active, its name is appended, e.g., 'hostname/room_name'.
    *   Status: Working.
*   **which**: Locate a command executable in the PATH.
    *   Usage: `$ which <command>`
    *   Notes: Searches the directories specified in the `PATH` environment variable. Prioritizes Python (`.py`) module files over script files without an extension if both exist, matching the kernel's command resolution logic.
    *   Status: Working.
*   **who**: Display who is logged on.
    *   Usage: `$ who`
    *   Notes: Displays a list of all logged-in users, their device, and login time.
    *   Status: Working.
*   **whoami**: Display the current username or device.
    *   Usage: `$ whoami [-d]`
    *   Options: `-d` (Display the name of the current device, stripping the `/dev/` prefix for cleaner output.)
    *   Notes: Displays the current username by default.
    *   Status: Working.
*   **xargs**: Build and execute command lines from standard input.
    *   Usage: `... | xargs [options] [command [initial-arguments]]`
    *   Options: `-n <max-args>` (use at most `max-args` arguments per command line); `-I <replace-str>` (replace occurrences of `replace-str` in initial arguments); `--help` (display help).
    *   Notes: Reads items from standard input, delimited by spaces or newlines. If no command is given, `echo` is used by default. Options `-I` and `-n` are mutually exclusive. The `-p` (prompt for execution) option is problematic in non-interactive environments, and `stderr` output from `-t` or non-existent commands is not directly visible in chat.
    *   Status: Working (with noted behaviors for `-p` and `stderr` visibility).

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

