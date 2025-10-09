GENERAL_HELP_MESSAGE = """
HELP FOR IOSK

Any time you run a command ("$ ") or write a comment ("# "), you are the only one that can see these and their output. So be sure to talk without command or comment if you're trying to reach other users in the room.


The following commands are generally available:

General Utilities:
    $ clear         - clear the session history for bots or the screen for console users
    $ date          - display the current date and time
    $ echo          - display the given arguments
    $ exit          - leave the system chat (logout)
    $ help          - get help on commands (this file)
    $ hostname      - display or set the system's hostname
    $ status        - display system status (date, whoami, users)
    $ ver           - display the current version of SideKick/IOSK
    $ welcome       - display a welcome message (auto-called on login)

Command and Shell:
    $ alias         - manage IOSK command aliases
    $ export        - set or display environment variables
    $ history       - show recent command history for this session
    $ skrip         - execute a skrip file or command string
    $ sleep         - pause execution for a specified amount of time
    $ system        - execute a command in the underlying host system
    $ trace         - manage the IOSK system-wide tracing facility
    $ watch         - execute a command repeatedly, displaying its output (console only)
    $ which         - locate a command executable in the PATH
    $ xargs         - build and execute command lines from standard input

Memory Management (Skrip Banks):
    $ bank          - load a skrip into core memory by executing it
    $ banks         - list memory accounts currently banked
    $ bankrupt      - clear core memory bank

Process Management:
    $ kill          - terminate a running process
    $ ps            - list currently running processes
    $ top           - provide a single, non-interactive snapshot of system activity

User/Device Management:
    $ ask           - ask an AI device (user) a question, with optional files
    $ attach        - attach a device as a user (bring user online)
    $ detach        - disconnect a device user (forced exit)
    $ login         - log in as a different user (logout current, new session for target)
    $ pause         - pause a bot user's AI engagement
    $ reattach      - reattach a user (or self) to a different device
    $ reset         - reset a user's session to a clean state
    $ su            - execute a command as another user (superuser only)
    $ unpause       - unpause a bot user's AI engagement
    $ users         - list connected users
    $ whatami       - see your current device name
    $ who           - display who is logged on, their device, and login time
    $ whoami        - see your current username

File and Directory Management:
    $ cd            - change the current working directory
    $ cp            - copy file or directory
    $ ls            - list files and directories (also: ll)
    $ mkdir         - create empty directory
    $ mv            - move/rename file or directory
    $ patch         - apply a diff to a file
    $ pwd           - print the name of the current working directory
    $ replace       - replaces occurrences of a string in a file with another string
    $ rm            - remove file
    $ rmdir         - remove empty directory
    $ touch         - create empty file
    $ tree          - recursively list as a tree (efficient; some folders hidden by .skignore)

Viewing and Analyzing Files:
    $ cat           - print file contents
    $ describe      - describe a file or directory (type, size, counts)
    $ diff          - show differences between two text files
    $ get           - get the contents of a file (alias for cat)
    $ grep          - search for PATTERN in each FILE or standard input
    $ head          - print first few lines of file
    $ search        - search for a term within text files
    $ send          - send file contents or piped data to the chat (to all users)
    $ tail          - print last few lines of file
    $ ticket        - view ticket details from the database
    $ tokens        - calculate total bytes and estimate tokens for session context
    $ wc            - count lines, words, and characters in a file

Networking & Chat Room Management:
    $ clroom        - close the active chat room
    $ mesh          - connect to other IOSK systems or view the current network mesh
    $ on            - execute a command on a remote, connected host
    $ port          - controls the network listener service
    $ room          - opens a new local chat room
    $ rooms         - list all rooms created on the local system
    $ topic         - view or set the topic for the current chat room
    $ unmesh        - disconnect from one or more peer IOSK systems
    $ where         - display a list of all known users across the network mesh
    $ whereami      - display the configured hostname and active room of the local IOSK system

System Lifecycle (kernel commands):
    $ init          - system initialization
    $ shutdown      - stop the system

Most commands accept --help as option.

More commands might be found by exploring the filesystem bin directories, e.g.:
    $ ls /bin
    $ ls /sbin

Note: bin files (commands) with a .py extension are called without an extension.

"""

async def iocall(io, argv):
    """Display general help or command-specific help.

    Usage: help
           help <command>
           help [-h|--help]

    help:             Displays the general IOSK help message.
    help <command>:   Displays the help message for the specified <command>.
                      This is equivalent to running `<command> --help`.
    -h, --help:       Displays this help message for the 'help' command itself.
    """

    # Handle the 'help' command's own help message
    if '-h' in argv or '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    # Handle command-specific help (e.g., `help echo`)
    if len(argv) == 1:
        command_name = argv[0]

        # Special handling for built-in commands
        if command_name in ('exit', 'logout'):
            await io.print(f"Usage: {command_name}\n\nExits the current IOSK session.")
            return True

        # io.os.call is expected to handle execution, including error messages
        # if the command doesn't exist or doesn't support --help.
        # We construct the command string as it would be typed in the shell.
        return await io.os.call(io, f"{command_name} --help")

    # Handle general help (no arguments)
    if not argv:
        await io.print(GENERAL_HELP_MESSAGE)
        return True

    # If we reach here, it means invalid arguments were provided (e.g., `help cmd1 cmd2`)
    await io.error("!! help: too many arguments or unknown option. Use 'help --help' for usage.")
    return False
