from datetime import datetime

async def iocall(io, argv):
    """Display who is logged on.

    Usage: who
           who --help

    Displays a list of all logged-in users, their device, and login time.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if not io.os.users:
        # This case is unlikely if the user running `who` is logged in,
        # but it is good practice to handle it.
        await io.print(":: no users are logged in.")
        return True

    users_data = []
    max_user_len = 0
    max_dev_len = 0

    # First pass: gather data and calculate column widths
    for user_io in io.os.users.values():
        user = user_io.user
        device = user_io.dev
        login_time = user_io.login_time

        users_data.append((user, device, login_time))

        if len(user) > max_user_len:
            max_user_len = len(user)
        if len(device) > max_dev_len:
            max_dev_len = len(device)

    # Add some padding to the column widths for spacing
    max_user_len += 2
    max_dev_len += 2

    # Second pass: print formatted data, sorted by username
    for user, device, login_time in sorted(users_data, key=lambda x: x[0]):
        time_str = login_time.strftime('%b %d %H:%M') if login_time else 'unknown'
        await io.print(f"{user:<{max_user_len}}{device:<{max_dev_len}}{time_str}")

    return True

