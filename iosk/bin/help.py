# Constants for general help message to match original /bin/help
GENERAL_HELP_MESSAGE = """
HELP FOR IOSK

Any time you run a command ("$ ") or write a comment ("# "), you are the only one that can see these and their output. So be sure to talk without command or comment if you're trying to reach other users in the room.


The following commands are generally available:
    $ help          - get help on commands (this file)
    $ exit          - leave the system chat

Mmory management:
    $ bank          - load some skrip accounts from /bank into core memory
    $ banks         - list memory accounts currently banked
    $ bankrupt      - clear core memory bank

Mnaging users:
    $ whoami        - see your current username
    $ users         - list connected users
    $ attach        - connect a user
    $ detach        - disconnect a user

Working with paths (files and directories):
    $ ls            - list files and directories (also: ll)
    $ tree          - recursively list as a tree (efficient; some folders hidden)
    $ mkdir         - Create empty directory
    $ rmdir         - Remove empty directory
    $ touch         - Create empty file
    $ rm            - Remove file
    $ cp            - Copy file
    $ mv            - Move/rename file or directory

Viewing files:
    $ cat           - print file contents
    $ head          - print first few lines of file
    $ tail          - print last few lines of file

System lifecycle:
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

