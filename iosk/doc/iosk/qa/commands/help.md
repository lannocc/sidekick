# /bin/help
**Description:** Displays general IOSK system usage information and a list of available commands. When provided with a command name, it displays detailed help for that specific command.
**Usage:**
    `$ help` - Displays general system help.
    `$ help <command>` - Displays specific help for the given command.
    `$ help --help` - Displays this help message.

**Examples:**
To display the general help message:
`$ help`

To display specific help for the `skrip` command:
`$ help skrip`
Output:
```
Execute a skrip file or command.

    Usage: skrip <filename>
           skrip -e <command>
           skrip --help

    <filename>: The path to the skrip file to execute.
    -e <command>: Execute the given command string.
    --help: Displays this help message.
```

To display specific help for the `ls` command:
`$ help ls`
Output:
```
List directory contents.

    Usage: ls [options] [path ...]
           ls --help

    Options:
      -l        Use a long listing format.
      -a        List all entries, including those starting with '.'.
      -h --help Display this help message.

    [path ...]: The paths to list. If no path is provided use current directory.

    Note: This command honors .skignore files in listed directories.
```

**Status:** Fully functional. The `help` command correctly displays general system information when run without arguments, and provides detailed, command-specific help when a command name is supplied. It no longer throws an exception when arguments are provided.
