async def iocall(io, argv):
    """Show recent command history for this session.

    Usage: history [N]
           history --help

    [N]: The number of most recent commands to show. If omitted, the entire session history is displayed.
    --help: Displays this help message.

    Note: Only lines entered as commands ($ ...) are stored in history.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    limit = None
    if argv:
        try:
            limit = int(argv[0])
            if limit <= 0:
                await io.error("!! history: N must be a positive number.")
                return False
        except ValueError:
            await io.error(f"!! history: invalid argument '{argv[0]}'. Expecting a number.")
            return False

    history_list = io.history
    if not history_list:
        await io.print(":: no history yet for this session.")
        return True

    if limit is not None:
        # Get the last 'limit' items
        history_to_show = history_list[-limit:]
        start_index = len(history_list) - len(history_to_show)
    else:
        history_to_show = history_list
        start_index = 0

    for i, command in enumerate(history_to_show, start=start_index + 1):
        await io.print(f"{i: >4}  {command}")

    return True

