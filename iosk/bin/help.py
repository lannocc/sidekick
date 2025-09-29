GENERAL_HELP_MESSAGE = """
HELP FOR IOSK

Any time you run a command ("$ ") or write a comment ("# "), you are the only one that can see these and their output. So be sure to talk without command or comment if you're trying to reach other users in the room.


The following commands are generally available:

General Utilities:
    $ help          - get help on commands (this file)
    $ alias         - manage IOSK command aliases
    $ date          - display the current date and time
    $ echo          - display the given arguments
    $ export        - set or display environment variables
    $ history       - show recent command history for this session
    $ status        - display system status (date, whoami, users)
    $ which         - locate a command executable in the PATH
    $ welcome       - display a welcome message (auto-called on login)
    $ exit          - leave the system chat (logout)

Memory Management (Skrip Banks):
    $ bank          - load some skrip accounts from /bank into core memory
    $ banks         - list memory accounts currently banked
    $ bankrupt      - clear core memory bank

User Management:
    $ whoami        - see your current username
    $ users         - list connected users
    $ attach        - attach a device as a user (bring user online)
    $ detach        - disconnect a device user (forced exit)
    $ ask           - ask an AI device (user) a question, with optional files
    $ su            - execute a command as another user (superuser only)

File and Directory Management:
    $ pwd           - print the name of the current working directory
    $ cd            - change the current working directory
    $ ls            - list files and directories (also: ll)
    $ tree          - recursively list as a tree (efficient; some folders hidden by .skignore)
    $ mkdir         - create empty directory
    $ rmdir         - remove empty directory
    $ touch         - create empty file
    $ rm            - remove file
    $ cp            - copy file or directory
    $ mv            - move/rename file or directory
    $ patch         - apply a diff to a file

Viewing and Analyzing Files:
    $ cat           - print file contents
    $ get           - get the contents of a file (alias for cat)
    $ head          - print first few lines of file
    $ tail          - print last few lines of file
    $ describe      - describe a file or directory (type, size, counts)
    $ diff          - show differences between two text files
    $ search        - search for a term within text files
    $ wc            - count lines, words, and characters in a file

System Interaction:
    $ skrip         - execute a skrip file or command string
    $ system        - execute a command in the underlying host system

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

        # Special handling for 'exit'
        if command_name == 'exit':
            await io.print("Usage: exit\n\nExits the current IOSK session.")
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

