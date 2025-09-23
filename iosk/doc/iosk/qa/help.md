HELP FOR IOSK
Any time you run a command ("$ ") or write a comment ("# "), you are the only one that can see these and their output. So be sure to talk without command or comment if you're trying to reach other users in the room.
The following commands are generally available:
    $ help          - get help on commands (this skrip)
    $ exit          - leave the system chat
For memory management:
    $ bank          - load some skrip accounts from /bank into core memory
    $ banks         - list memory accounts currently banked
    $ bankrupt      - clear core memory bank
For managing users:
    $ whoami        - see your current username
    $ users         - list connected users
    $ attach        - connect a user
    $ detach        - disconnect a user
For working with paths (files and directories):
    $ ls            - list files and directories (also: ll)
    $ tree          - recursively list as a tree (efficient; some folders hidden)
    $ mkdir         - Create empty directory
    $ rmdir         - Remove empty directory
    $ touch         - Create empty file
    $ rm            - Remove file
    $ cp            - Copy file
    $ mv            - Move/rename file or directory
For viewing files:
    $ cat           - print file contents
    $ head          - print first few lines of file
    $ tail          - print last few lines of file
For system control:
    $ init          - start the system
    $ shutdown      - stop the system
Most commands accept --help as option.
More commands might be found by exploring the filesystem bin directories, e.g.:
    $ ls /bin
    $ ls /sbin
Note: bin files (commands) with a .py extension are called without an extension.
