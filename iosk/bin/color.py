import argparse
from sk.iosk.util import COLOR_MAP, REVERSE_COLOR_MAP, ANSI_RESET

async def iocall(io, argv):
    """View or set user colors for chat messages.

    Usage: color [--help] [-u USER[.HOST]] [COLOR]

    This command manages the colors you see for users in chat.
    AI agents do not use colors.

    Arguments:
      COLOR        The name of the color to set. If omitted, shows the
                   current color. See available colors below.

    Options:
      -u, --user USER[.HOST]  Target another user. If specified, you will view or
                              set the color for that specific user. Can be a local
                              user or a network user (e.g., alice.mars).
      --help                  Displays this help message.

    Available Colors:
    black, red, green, yellow, blue, magenta, cyan, white
    bright_black, bright_red, bright_green, bright_yellow,
    bright_blue, bright_magenta, bright_cyan, bright_white
    """
    if io.session.bot:
        await io.error("!! color: this command is not available for your device.")
        return False

    parser = argparse.ArgumentParser(prog='color', description='View or set user colors.', add_help=False)
    parser.add_argument('-u', '--user', help='The target user, e.g., "bob" or "alice.mars".')
    parser.add_argument('color', nargs='?', help='The color to set.')
    parser.add_argument('--help', action='store_true', help='Show help message.')

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse tries to exit on error, catch it
        await io.error("!! color: invalid arguments. See `color --help`.")
        return False

    if args.help:
        await io.print(iocall.__doc__)
        return True

    target_user_str = args.user if args.user else io.session.user
    new_color_name = args.color

    # Resolve target_user_str to a full user.host address
    if '.' in target_user_str:
        target_addr = target_user_str
    else:
        target_addr = f"{target_user_str}.{io.os.hostname}"

    # Check if the target user is known
    if target_addr not in io.session.user_colors:
        await io.error(f"!! color: user '{target_user_str}' not found or is not a color-enabled user.")
        return False

    if new_color_name:
        # Set a new color
        if new_color_name not in COLOR_MAP:
            await io.error(f"!! color: invalid color '{new_color_name}'. See `color --help` for available colors.")
            return False

        color_code = COLOR_MAP[new_color_name]
        io.session.user_colors[target_addr] = color_code
        display_target = 'Your color' if target_user_str == io.session.user else f"Color for {target_user_str}"
        await io.print(f":: {display_target} set to {color_code}{new_color_name}{ANSI_RESET}")

        # Broadcast the color change to network clients
        if io.os.port:
            await io.os.broadcast_color_updates()

        return True
    else:
        # View the current color
        current_code = io.session.user_colors.get(target_addr, '')
        current_name = REVERSE_COLOR_MAP.get(current_code, 'none')
        display_target = 'Your color is' if target_user_str == io.session.user else f"Color for {target_user_str} is"
        await io.print(f":: {display_target} {current_code}{current_name}{ANSI_RESET}")
        return True

