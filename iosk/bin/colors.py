COLOR_MAP = {
    'black': '\033[30m', 'red': '\033[31m', 'green': '\033[32m', 'yellow': '\033[33m',
    'blue': '\033[34m', 'magenta': '\033[35m', 'cyan': '\033[36m', 'white': '\033[37m',
    'bright_black': '\033[90m', 'bright_red': '\033[91m', 'bright_green': '\033[92m',
    'bright_yellow': '\033[93m', 'bright_blue': '\033[94m', 'bright_magenta': '\033[95m',
    'bright_cyan': '\033[96m', 'bright_white': '\033[97m',
}
REVERSE_COLOR_MAP = {v: k for k, v in COLOR_MAP.items()}
RESET_CODE = '\033[0m'


async def iocall(io, argv):
    """Display the chat colors for all connected users.

    Usage: colors
           colors --help

    This command shows a list of all known users and the color you
    see their chat messages in.

    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return

    if io.bot:
        await io.error("!! colors: this command is not available for your device.")
        return False

    await io.print("User Colors (your perspective):")
    if not io.user_colors:
        await io.print("  (No users with colors found)")
        return True

    # Sort by username for a consistent, readable output
    sorted_users = sorted(io.user_colors.keys())

    # Find the longest username for alignment
    max_len = max(len(user) for user in sorted_users) if sorted_users else 0

    for user in sorted_users:
        code = io.user_colors[user]
        name = REVERSE_COLOR_MAP.get(code, 'unknown')
        
        # Format with padding for alignment
        padding = ' ' * (max_len - len(user) + 4)
        await io.print(f"  {user}{padding}{code}{name}{RESET_CODE}")
    
    return True
