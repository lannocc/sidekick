## /bin Commands

These commands are generally available to users within the IOSK environment. Most `/bin` commands also accept `--help` as an option to display their specific help message.

*   **alias**: Manage IOSK command aliases.
    *   Usage: `$ alias` (list) or `$ alias NAME=VALUE` (define/update) or `$ alias --help`
    *   Notes: `NAME=VALUE` defines a new alias or updates an existing one. NAME is the alias, VALUE is the command it expands to. Variables within an alias definition (e.g., `$PATH`) are expanded *during the alias definition itself*, not during alias execution. The parser struggles with nested quotes in alias definitions.
    *   Status: Working (with caveats - alias quoting and variable expansion issues exist but are not a high priority to resolve immediately given the parser status).
*   **ask**: Ask an AI a question, with optional file/directory context.
    *   Usage: `$ ask [options] <prompt>` or `... | ask [options]` or `$ ask --help`
    *   Options:
        *   `-h`, `--help`: Displays this help message.
        *   `-q`, `--quiet`: Quiet mode. Only print the final AI response.
        *   `-f <file>`: Attach the contents of the specified file to the prompt. Can be specified multiple times.
        *   `-p <directory>`: Package and attach the contents of the specified directory. Can be specified multiple times.
        *   `-e <lang> <file>`: Extract the first markdown code block of `<lang>` from the response and save it to `<file>`.
        *   `-1`: Use model: `gemini-2.0-flash-lite`.
        *   `-2`: Use model: `gemini-2.5-flash` (default).
        *   `-3`: Use model: `gemini-2.5-pro`.
    *   Notes: If `<prompt>` is not provided as an argument, it is read from standard input.
    *   Status: Working.
*   **attach**: Attach a device as a user.
    *   Usage: `$ attach <device> [handle]` or `$ attach --help`
    *   Notes: `handle` defaults to `device` if not provided and is normalized to replace '/' with '-'. Requires an active chat system and will bring the attached user into the current active room.
    *   Status: Working.
*   **bank**: Load a file's content into core memory banks.
    *   Usage: `$ bank <path components...>` or `... | bank` or `$ bank --help`
    *   Notes: If the file has a shebang (e.g., `#!/bin/skrip`), it is executed and its output is captured. Otherwise, the raw file content is loaded directly. The path can be absolute (e.g., `/etc/skrc`), relative to the CWD (e.g., `./myskrip`), or relative to `/bank` (e.g., `role devops`). If a given path is not found and it does not already end with .md, the command will also try to find the file by appending a .md extension. If input is piped, the content is loaded directly into memory without being executed as a skrip.
    *   Status: Working.
*   **bankrupt**: Clear all loaded banks from core memory.
    *   Usage: `$ bankrupt` or `$ bankrupt --help`
    *   Notes: Removes all entries from `io.banks`.
    *   Status: Working.
*   **banks**: List memory accounts currently banked.
    *   Usage: `$ banks` or `$ banks --help`
    *   Notes: Prints the virtual paths (keys) of all loaded memory banks.
    *   Status: Working.
*   **cat**: Display the contents of a file.
    *   Usage: `$ cat <filename>` or `$ cat --help`
    *   Notes: Requires a filename argument.
    *   Status: Working.
*   **cd**: Change the current working directory.
    *   Usage: `$ cd [directory]` or `$ cd --help`
    *   Notes: If no directory is specified, it changes to the user's home directory (`/home/<user>`).
    *   Status: Working.
*   **clear**: Clear the session history for bots or the screen for console users.
    *   Usage: `$ clear` or `$ clear --help`
    *   Notes: For bot users, this command clears the entire chat session history, leaving only the `clear` command itself as the first and only entry. This effectively provides a clean slate for the bot's context. For interactive console/terminal users, this command clears the screen using ANSI escape sequences.
    *   Status: Working.
*   **clroom**: Close the active chat room.
    *   Usage: `$ clroom` or `$ clroom --help`
    *   Notes: Closes the single active chat room on the local system. This command can typically only be run by the room's owner or a superuser.
    *   Status: Working.
*   **cp**: Copy a file or directory.
    *   Usage: `$ cp <source> <destination>` or `$ cp --help`
    *   Notes: Handles file-to-file copy and file-to-existing-directory copy. Errors if source does not exist.
    *   Status: Working.
*   **date**: Display the current date and time, with optional formatting.
    *   Usage: `$ date` or `$ date <format>` or `$ date --help`
    *   Notes: `<format>` is a format string to control the output. It should start with a `+` (e.g., `"+%Y%m%d_%H%M%S"`), using Python's `datetime strftime` format codes. If no format is provided, a default format is used.
    *   Status: Working.
*   **describe**: Describe a file or directory.
    *   Usage: `$ describe <path>` or `$ describe --help`
    *   Notes: Provides a concise summary: type, size, line/word counts for text, simple type heuristics.
    *   Status: Working.
*   **detach**: Detach a device user.
    *   Usage: `$ detach <handle>` or `$ detach --help`
    *   Notes: Requires a username/handle argument. The target user must be currently attached.
    *   Status: Working.
*   **diff**: Show differences between two text files.
    *   Usage: `$ diff [-u N] <file1> <file2>` or `$ diff --help`
    *   Options:
        *   `-u N`: Unified context lines (default 3).
    *   Notes: Files must be text; binary files are refused by the system.
    *   Status: Working.
*   **echo**: Echo the given arguments.
    *   Usage: `$ echo [arguments]` or `$ echo --help`
    *   Notes: Prints arguments as a single space-separated string.
    *   Status: Working.
*   **export**: Set or display environment variables.
    *   Usage: `$ export [NAME=VALUE] ...` or `$ export --help`
    *   Notes: With no arguments, `export` prints a list of all environment variables. Otherwise, it sets each `NAME` to `VALUE`. Values are stored after stripping a single layer of quotes.
    *   Status: Working.
*   **get**: Get the contents of a file.
    *   Usage: `$ get <filename>` or `$ get --help`
    *   Notes: Behaves identically to `cat`. Requires a filename argument.
    *   Status: Working.
*   **grep**: Search for a regular expression PATTERN in each FILE or standard input.
    *   Usage: `$ grep [OPTIONS] PATTERN [FILE...]` or `$ grep --help`
    *   Options:
        *   `-i`, `--ignore-case`: Ignore case distinctions in PATTERN.
        *   `-v`, `--invert-match`: Invert the sense of matching, to select non-matching lines.
        *   `-n`, `--line-number`: Prefix each line of output with the 1-based line number within its input file.
        *   `-l`, `--files-with-matches`: Suppress normal output; instead print the name of each input file from which output would normally have been printed.
        *   `-c`, `--count`: Suppress normal output; instead print a count of matching lines for each input file.
        *   `-r`, `-R`, `--recursive`: Read all files under each directory, recursively.
    *   Notes: If no files are given, reads from standard input.
    *   Status: Working.
*   **head**: Display the first N lines of a file or stdin.
    *   Usage: `$ head [-n <number>] [filename]` or `$ head --help`
    *   Options:
        *   `-n <number>`: Specifies the number of lines to display. Defaults to 10.
    *   Notes: If `filename` is omitted, reads from `stdin`.
    *   Status: Working.
*   **help**: Display general help or command-specific help.
    *   Usage: `$ help` or `$ help <command>` or `$ help [-h|--help]`
    *   Notes: `help` displays the general IOSK help message. `help <command>` displays the help message for the specified command (equivalent to `<command> --help`).
    *   Status: Fully functional.
*   **history**: Show recent command history for this session.
    *   Usage: `$ history [N]` or `$ history --help`
    *   Notes: `[N]` is the number of most recent commands to show. If omitted, the entire session history is displayed. Only lines entered as commands (`$ ...`) are stored in history.
    *   Status: Working.
*   **hostname**: Display or set the system's hostname.
    *   Usage: `$ hostname` or `$ hostname <new-hostname>` or `$ hostname --help`
    *   Notes: `hostname` prints the current hostname as configured in `/etc/hostname`. `hostname <new-hostname>` sets the system's hostname to the new value, updating both the `/etc/hostname` file and the current runtime configuration.
    *   Status: Working.
*   **kill**: Terminate a running process.
    *   Usage: `$ kill <pid>` or `$ kill --help`
    *   Notes: `<pid>` is the Process ID (PID) of the process to terminate. Use the `ps` command to find the PIDs of running processes.
    *   Status: Working.
*   **ll**: Lists directory contents using the long listing format (alias for `ls -l`).
    *   Usage: `$ ll [path ...]`
    *   Notes: Provides one entry per line with detailed information. This command is an alias for `ls -l`.
    *   Status: Working (as an alias).
*   **login**: Log in as a different user.
    *   Usage: `$ login <username>` or `$ login --help`
    *   Notes: Logs out the current session and starts a new session for the specified user on the same device. This is useful for switching users without restarting the system.
    *   Status: Working.
*   **ls**: List directory contents.
    *   Usage: `$ ls [options] [path ...]` or `$ ls --help`
    *   Options:
        *   `-l`: Use a long listing format.
        *   `-a`: List all entries, including those starting with '.'.
    *   Notes: Hides system dotfiles (`.`, `..`, `__pycache__`, `~`-ending files) by default unless `-a` is used.
    *   Status: Working.
*   **mesh**: Connect to other IOSK systems or view the current network mesh.
    *   Usage: `$ mesh [-s | --simple]` or `$ mesh <host[:port]>` or `$ mesh --help`
    *   Options:
        *   `-s`, `--simple`: Use a compact, single-column format: 'hostname'. The local host is indicated by a leading tilde (~), and an asterisk (*) if its listener is open. Address details like '[ip:port]' or '[via host]' are omitted in this mode.
    *   Notes:
        *   `mesh` (no arguments, or with `-s`) lists all currently connected peer systems in the network mesh, including both direct and indirect (routed) connections. The local system's hostname is prepended with a tilde (~). If the local system has its listener port open, an asterisk (*) is appended to its hostname.
        *   `mesh <host[:port]>` establishes an outbound connection to another IOSK system's listener service. If the port is not specified, it defaults to 4209.
    *   Status: Working.
*   **mkdir**: Create a directory.
    *   Usage: `$ mkdir <directory>...` or `$ mkdir -p <directory>...` or `$ mkdir --help`
    *   Options:
        *   `-p`: Allows parent directories to be created.
    *   Notes: Multiple directories can be specified. Will error if the directory already exists or a path component is not a directory.
    *   Status: Working.
*   **mv**: Move or rename a file or directory.
    *   Usage: `$ mv <source> <destination>` or `$ mv --help`
    *   Notes: If `DESTINATION` is an existing directory, `SOURCE` is moved into it. If `DESTINATION` is a filename, `SOURCE` is renamed to `DESTINATION`. Errors if `SOURCE` does not exist or if `DESTINATION` is a non-existent directory.
    *   Status: Working.
*   **on**: Execute a command on a remote, connected host.
    *   Usage: `$ on <host> <command...>` or `$ on --help`
    *   Notes: `<host>` is the hostname of a connected peer system in the network mesh. `<command...>` is the command and its arguments to execute on the remote host. The command's output is streamed back and displayed locally.
    *   Status: Working.
*   **patch**: Apply a diff to a file.
    *   Usage: `$ patch <targetfile> <patchfile>` or `$ patch --help`
    *   Notes: This initial version can apply simple line-based diffs (unified diff format) to a target file.
    *   Status: Working.
*   **pause**: Pause a bot user's AI engagement.
    *   Usage: `$ pause [username]` or `$ pause --help`
    *   Notes: Pauses the AI engagement for the specified bot user. The bot will stop making AI trips and will not receive new chat messages until unpaused. If no username is provided, this command attempts to pause the current user. The console user cannot be paused.
    *   Status: Working.
*   **port**: Controls the network listener service.
    *   Usage: `$ port` or `$ port on [port_num]` or `$ port off` or `$ port --help`
    *   Notes:
        *   `port`: Displays the current status of the network listener.
        *   `port on [port_num]`: Starts the listener service on the specified port. Defaults to 4209.
        *   `port off`: Stops the listener service and closes all connections.
    *   Status: Working.
*   **ps**: List currently running processes.
    *   Usage: `$ ps` or `$ ps --help`
    *   Notes: Displays information about active processes, including their PID, the user who started them, their running time, and the command.
    *   Status: Working.
*   **pwd**: Print the name of the current working directory.
    *   Usage: `$ pwd` or `$ pwd --help`
    *   Notes: Does not accept arguments.
    *   Status: Working.
*   **reattach**: Reattach a user to a different device.
    *   Usage: `$ reattach <device> [user]` or `$ reattach --help`
    *   Notes: `<device>` is the name of the device (e.g., 'dummy', 'google', 'openai/gpt-4). Corresponds to a path under `/dev/`. `[user]` is the username to reattach. If omitted, defaults to the current user. Special behavior for console devices (`/dev/console`): If a user is reattached to a console device that is already occupied, the two users will swap devices. The original console user will be attached to the device the other user was previously on.
    *   Status: Working.
*   **replace**: Replaces occurrences of a string in a file with another string.
    *   Usage: `$ replace <filename> <old_string> <new_string>`
    *   Notes: `<filename>` is the path to the file to modify. `<old_string>` is the string to search for. `<new_string>` is the string to replace with.
    *   Status: Working.
*   **reset**: Reset a user's session to a clean state.
    *   Usage: `$ reset [username]` or `$ reset --help`
    *   Notes: Clears session history, command history, loaded banks, environment variables, aliases, and resets the current working directory to the user's home. Then, it re-runs the system-wide `/etc/skrc` and the user's `~/.skrc` file, simulating a fresh login. If no username is provided, it resets the current user's session. Only superusers can reset the session of another user.
    *   Status: Working.
*   **rm**: Remove files.
    *   Usage: `$ rm <filename>...` or `$ rm --help`
    *   Notes: This command does not support removing directories. Use `rmdir` for empty directories. Multiple files can be specified.
    *   Status: Working for files, but explicitly fails for directories (which is expected for a basic `rm` command).
*   **rmdir**: Remove one or more directories.
    *   Usage: `$ rmdir <directory>...` or `$ rmdir --help`
    *   Notes: This command only removes empty directories. Multiple directories can be specified.
    *   Status: Working.
*   **room**: Opens a new local chat room.
    *   Usage: `$ room [room_name]` or `$ room --help`
    *   Notes: Opens a new chat room on the local system with the specified name. If no `room_name` is provided, it defaults to 'iosk'. Only one room can be active at a time. This command will fail if a room is already open.
    *   Status: Working.
*   **rooms**: List all rooms created on the local system.
    *   Usage: `$ rooms [-s | --simple]` or `$ rooms --help`
    *   Options:
        *   `-s`, `--simple`: Use a compact, single-column format. Active rooms are indicated with a leading tilde (~) and user count, e.g., `~iosk(2)`.
    *   Notes: By default, lists all rooms in a verbose, multi-column format showing ROOM and TOPIC. The currently active room, if any, is indicated with a leading tilde (~), followed by the count of active users in parentheses, e.g., `~iosk(2)`.
    *   Status: Working.
*   **search**: Search for a term within text files or stdin.
    *   Usage: `$ search [-i] [-n] [-l] [-c] <term> [path ...]` or `$ search --help`
    *   Options:
        *   `-i`: Case-insensitive search.
        *   `-n`: Show line numbers.
        *   `-l`: List filenames with matches only.
        *   `-c`: Print count of matches per file.
    *   Notes: If no paths are given, reads from standard input. If `stdin` is empty, it defaults to `/home/<user>` if it exists; otherwise `/`. The term can contain spaces if properly quoted in the shell.
    *   Status: Working.
*   **send**: Send file contents or piped data as a message to the chat.
    *   Usage: `$ send [-u <user>]... <file>...` or `... | send [-u <user>]...` or `$ send --help`
    *   Options:
        *   `-u <user>`: Send a direct message to a specific user. This option can be used multiple times to specify multiple recipients in `user` or `user.host` format.
    *   Notes: Reads the contents of one or more files, or reads from standard input, and sends the result as a raw text message. By default, the message is broadcast to other users in the current chat.
    *   Status: Working.
*   **skrip**: Execute a skrip file or command.
    *   Usage: `$ skrip <filename>` or `$ skrip -e <command>` or `$ skrip -s <filename>` or `$ skrip --help`
    *   Notes:
        *   `<filename>` (default mode): The path to the skrip file to execute. Lines starting with `$ ` are commands; other lines are printed.
        *   `-e <command>`: Execute the given command string in default mode.
        *   `-s <filename>`: Execute the given file in "pure shell mode". All non-comment lines are treated as commands and do not need a `$ ` prefix.
    *   Status: Working.
*   **sleep**: Pause execution for a specified amount of time.
    *   Usage: `$ sleep <duration>...` or `$ sleep --help`
    *   Notes: Pauses for an amount of time specified by the sum of the values of the command line arguments. Each argument is a number followed by an optional unit (s, m, h, d). Default unit is seconds. This command only blocks its own execution; the user can still receive chat messages while it runs. A direct message sent to a sleeping user will interrupt the sleep.
    *   Status: Working.
*   **status**: Displays system status information (date, user, users).
    *   Usage: `$ status`
    *   Notes: A skrip that calls `date`, `whoami`, and `users`.
    *   Status: Working.
*   **su**: Execute a command as another user, with optional piped input.
    *   Usage: `$ su <user> <command> [args...]` or `... | su <user> <command> [args...]` or `$ su --help`
    *   Notes: When standard input is piped to `su`, it is passed as standard input to the executed command.
    *   Status: Working.
*   **system**: Execute a command in the underlying host system.
    *   Usage: `$ system <command> [args...]` or `$ system --help`
    *   Notes: This command executes directly on the host OS and may have security implications. Use with caution. Arguments that are identified as absolute or relative paths (e.g., starting with '/', './', or '../') will be sandboxed to the host filesystem's equivalent path. The command will also execute in the host equivalent of the user's current working directory.
    *   Status: Working.
*   **tail**: Display the last N lines of a file or stdin.
    *   Usage: `$ tail [-n <number>] [filename]` or `$ tail --help`
    *   Options:
        *   `-n <number>`: Specifies the number of lines to display. Defaults to 10.
    *   Notes: If `filename` is omitted, reads from `stdin`.
    *   Status: Working.
*   **ticket**: View ticket details from the database.
    *   Usage: `$ ticket <ticket-number>` or `$ ticket --help`
    *   Notes: `<ticket-number>` is the ID of the ticket to view (e.g., 123 or T123). Requires database configuration in `/etc/`.
    *   Status: Working.
*   **tokens**: Calculate token usage for the current session context.
    *   Usage: `$ tokens` or `$ tokens --help`
    *   Notes: This command assembles the full context that would be sent to an AI, including the preamble, banked memory, chat history, and postamble, and reports its size. It also displays two running totals for the entire session: Session Total (caching) and Session Total (cumulative).
    *   Status: Working.
*   **top**: Provide a single, non-interactive snapshot of system activity.
    *   Usage: `$ top` or `$ top --help`
    *   Notes: Displays a summary of system status and a list of running processes, sorted by runtime in descending order. This is a one-shot command and does not update in real-time.
    *   Status: Working.
*   **topic**: View or set the topic for the current chat room.
    *   Usage: `$ topic` or `$ topic <new topic>` or `$ topic --help`
    *   Notes:
        *   `topic`: Displays the current room's topic.
        *   `<new topic>`: Sets the room's topic to the provided text. Only the room owner or a superuser can set the topic.
    *   Status: Working.
*   **touch**: Create an empty file.
    *   Usage: `$ touch <filename>` or `$ touch --help`
    *   Notes: Creates a new, empty file. If the file already exists, the command errors, unlike standard UNIX `touch` which updates the timestamp.
    *   Status: Working as a file creation utility, with non-standard behavior for existing files.
*   **trace**: Manage the IOSK system-wide tracing facility.
    *   Usage: `$ trace` or `$ trace on|off` or `$ trace <name> on|off` or `$ trace --help`
    *   Notes:
        *   `trace`: Displays a list of all available trace points and their current state (ON/OFF).
        *   `trace on|off`: Enables or disables all available trace points.
        *   `trace <name> on|off`: Enables or disables a single, specific trace point by its name.
    *   Status: Working.
*   **tree**: List directory contents recursively in a tree-like format.
    *   Usage: `$ tree [options] [path ...]` or `$ tree --help`
    *   Options:
        *   `-c`: Count bytes and estimate tokens for the content.
        *   `-d`: List directories only.
    *   Notes: Some files and folders are hidden (this command honors `.skignore` files). If no path is provided, uses the current directory.
    *   Status: Working.
*   **unmesh**: Disconnect from one or more peer IOSK systems.
    *   Usage: `$ unmesh [host...]` or `$ unmesh --help`
    *   Notes:
        *   `unmesh` (no arguments): Disconnects from all currently connected peer systems in the network mesh.
        *   `unmesh <host...>`: Disconnects from the specified peer systems.
    *   Status: Working.
*   **unpause**: Unpause a bot user's AI engagement.
    *   Usage: `$ unpause <username>` or `$ unpause --help`
    *   Notes: Resumes the AI engagement for a previously paused bot user. This command must be run by another user, as a paused user cannot execute commands.
    *   Status: Working.
*   **uptime**: Show how long the system has been running.
    *   Usage: `$ uptime` or `$ uptime --help`
    *   Notes: Displays the current time, how long the system has been running, and how many users are currently logged on.
    *   Status: Working.
*   **users**: List online users.
    *   Usage: `$ users` or `$ users --help`
    *   Notes: Prints the usernames of all currently connected users and a count.
    *   Status: Working.
*   **ver**: Display the current version of SideKick/IOSK.
    *   Usage: `$ ver` or `$ ver --help`
    *   Notes: Does not accept arguments. `--help` displays its own help message.
    *   Status: Working.
*   **watch**: Execute a command repeatedly, displaying its output. Console only.
    *   Usage: `$ watch [options] <command>` or `$ watch --help`
    *   Options:
        *   `-n <seconds>`: Specify the update interval. The command is executed every `<seconds>` seconds. The default is 2.0 seconds. Can be used as `-n<seconds>` or `-n <seconds>`.
        *   `-c`: Enable color. By default, ANSI color escape codes from the command's output are stripped. This option preserves them.
    *   Notes: This command is only available to users on a console device (e.g., `/dev/console`). To exit, press Ctrl-C, or use the `kill` command on this process's PID.
    *   Status: Working.
*   **wc**: Count lines, words, and characters in a file or stdin.
    *   Usage: `$ wc [file]` or `$ wc --help`
    *   Notes: If no file is specified, reads from standard input.
    *   Status: Working.
*   **welcome**: Displays a welcome message.
    *   Usage: `$ welcome`
    *   Notes: A simple skrip that prints "Welcome to IOSK!".
    *   Status: Working.
*   **where**: Display a list of all known users across the network mesh.
    *   Usage: `$ where [-s | --simple]` or `$ where --help`
    *   Options:
        *   `-s`, `--simple`: Use a compact, single-column format: 'user.host/room'. If a user is not in a room, the '/room' part is omitted. For the local host, the '.host' part is omitted. The user running the command is indicated with a leading tilde (~).
    *   Notes: By default, displays a verbose, multi-column format showing USER, HOST, and ROOM. The user running the command is indicated with a leading tilde (~). For the local host, the HOST column is blank.
    *   Status: Working.
*   **whereami**: Display the configured hostname and active room of the local IOSK system.
    *   Usage: `$ whereami` or `$ whereami --help`
    *   Notes: Displays the unique hostname of the local IOSK system on the network. If a chat room is active, its name is appended, e.g., 'hostname/room_name'.
    *   Status: Working.
*   **which**: Locate a command executable in the PATH.
    *   Usage: `$ which <command>` or `$ which --help`
    *   Notes: Searches the directories specified in the `PATH` environment variable. Prioritizes Python (`.py`) module files over script files without an extension if both exist, matching the kernel's command resolution logic.
    *   Status: Working.
*   **who**: Display who is logged on.
    *   Usage: `$ who` or `$ who --help`
    *   Notes: Displays a list of all logged-in users, their device, and login time.
    *   Status: Working.
*   **whoami**: Display the current username or device.
    *   Usage: `$ whoami [-d]` or `$ whoami --help`
    *   Options:
        *   `-d`: Display the name of the current device, stripping the `/dev/` prefix for cleaner output.
    *   Notes: Displays the current username by default.
    *   Status: Working.
*   **xargs**: Build and execute command lines from standard input.
    *   Usage: `... | xargs [options] [command [initial-arguments]]` or `... | xargs --help`
    *   Options:
        *   `-n <max-args>`: Use at most `max-args` arguments per command line.
        *   `-I <replace-str>`: Replace occurrences of `replace-str` in the initial-arguments with names read from standard input. This also implies that the command is executed once for each input item. The options `-I` and `-n` are mutually exclusive.
    *   Notes: Reads items from standard input, delimited by spaces or newlines. If no command is given, `echo` is used by default. Options `-I` and `-n` are mutually exclusive. The `-p` (prompt for execution) option is problematic in non-interactive environments, and `stderr` output from `-t` or non-existent commands is not directly visible in chat.
    *   Status: Working (with noted behaviors for `-p` and `stderr` visibility).

## /sbin Commands

These commands are typically used for system administration tasks. Most `/sbin` commands also accept `--help` as an option to display their specific help message.

*   **init**: System initialization script.
    *   Usage: (Called automatically by the system)
    *   Notes: Sets up the initial `PATH` and performs other system startup tasks. Not intended for direct user invocation.
    *   Status: Assumed Working. Needs NO further testing.
*   **shutdown**: Shut down the system.
    *   Usage: `$ shutdown` or `$ shutdown --help`
    *   Notes: Initiates the shutdown sequence for the IOSK system. This command signals the underlying operating system to halt the system.
    *   Status: Assumed working. No further testing required as execution interrupts the running system.

