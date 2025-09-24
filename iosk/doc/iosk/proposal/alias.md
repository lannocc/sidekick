## IOSK Aliases: A Proposal for Command Shortcuts

As noted in `todo.md`, the ability to define command aliases will significantly enhance user experience and productivity in IOSK. Aliases provide a mechanism for users to create custom, shorter names for frequently used or complex commands, reducing typing and streamlining workflows.

At its core, an alias is a textual substitution that the command interpreter performs before executing a command. For instance, a user might define `ll='ls -l'` so that typing `ll` executes `ls -l`. This feature is fundamental to many UNIX-like shells and will greatly improve the conversational efficiency within IOSK.

1. To manage aliases, a new command, `alias`, will be implemented in `/bin/alias.py`. This command will allow users to define new aliases (e.g., `$ alias myls='ls -aF'`), list currently defined aliases (e.g., `$ alias`), and potentially remove them. Each user's active aliases for a session will be stored in a dedicated dictionary within their `Context` object, such as `io.aliases`.

2. The alias resolution mechanism will be integrated into the kernel's command execution flow. Specifically, before `io.os.call` attempts to locate and execute a command from `/bin` or `/sbin`, it will first check if the command entered by the user matches an existing alias in `io.aliases`. If a match is found, the original command string will be replaced with the alias's defined value, and then the modified command string will be processed for execution. This ensures aliases are expanded correctly.

For persistence, aliases can be defined within the system's global startup script, `/etc/skrc`, for system-wide availability, or in a user's personal `~/.skrc` file for user-specific configurations. When a user logs in, the `skrip` command will execute these files, populating their `io.aliases` dictionary with their preferred shortcuts, making them available immediately upon session start.

This alias system will empower users with greater control over their IOSK environment, making it more adaptable and efficient. Future enhancements could include support for alias chaining, argument passing within aliases, and more sophisticated substitution rules.

