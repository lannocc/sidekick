# history.py

async def iocall(io, args):
    """Show recent command history for this session.

    Usage: history [N]
           history --help

    N: Number of most recent commands to show (default 20).
    Notes:
      - Only lines that were entered as commands ("$ ...") are shown.
    """
    if args is None:
        await io.error('!! history: bad args')
        return

    tokens = [t for t in args.split(' ') if t]
    if '--help' in tokens:
        await io.print(iocall.__doc__)
        return

    n = 20
    if len(tokens) == 1:
        try:
            n = int(tokens[0])
        except ValueError:
            await io.error('!! history: N must be a number')
            return
    elif len(tokens) > 1:
        await io.error('!! history: too many arguments')
        return

    # io.session contains prompts and inputs
    data = io.session.getvalue() if io.session else ''
    lines = data.splitlines()

    # Extract only commands: lines after the prompt that begin with "$ "
    # Prompts look like: "[user] >> "
    cmds = []
    for line in lines:
        # find prompt separator if present
        sep = ' >> '
        pos = line.find(sep)
        entered = line[pos+len(sep):] if pos != -1 else line
        if entered.startswith('$ '):
            cmds.append(entered[2:])  # strip "$ "

    start = max(0, len(cmds) - n)
    for idx, cmd in enumerate(cmds[start:], start=start+1):
        await io.print(f'{idx}  {cmd}')

    return True
