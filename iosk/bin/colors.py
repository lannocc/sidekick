from sk.iosk.util import COLOR_MAP, REVERSE_COLOR_MAP, RESET_CODE


async def iocall(io, argv):
    """Display the chat colors for all connected users.

    Usage: colors
           colors --help

    This command shows a list of all known users (local and network)
    and the color you see their chat messages in.

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

    # Sort by the full user.host address for a consistent, readable output
    sorted_user_addrs = sorted(io.user_colors.keys())

    # Create display names and find the longest one for alignment
    display_names = {}
    for addr in sorted_user_addrs:
        user, host = addr.split('.', 1)
        if host == io.os.hostname:
            display_names[addr] = user
        else:
            display_names[addr] = addr
    
    max_len = max(len(name) for name in display_names.values()) if display_names else 0

    for addr in sorted_user_addrs:
        display_name = display_names[addr]
        code = io.user_colors[addr]
        name = REVERSE_COLOR_MAP.get(code, 'unknown')
        
        # Format with padding for alignment
        padding = ' ' * (max_len - len(display_name) + 4)
        await io.print(f"  {display_name}{padding}{code}{name}{RESET_CODE}")
    
    return True
