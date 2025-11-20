import asyncio

DOCSTRING = """Configure the rolling session history cutoff.

Usage: rolling [--help]
       rolling on|off
       rolling --<mode> <limit>

When enabled, the oldest history entries are automatically removed to keep
the session context within a configured limit.

Modes:
  --tokens   Limit by total token count.
  --bytes    Limit by total byte count.
  --lines    Limit by total line count.
  --prompts  Limit by total number of entries (prompts).

Examples:
  rolling              # Display the current configuration
  rolling on           # Enable the currently configured cutoff
  rolling off          # Disable the cutoff
  rolling --tokens 8000 # Set cutoff to 8000 tokens and enable it
"""

async def iocall(io, argv):
    """Handle the 'rolling' command execution."""
    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    config = io.session.rolling_config

    if len(argv) == 0:
        # Display current status
        enabled = config.get('enabled', False)
        if enabled:
            mode = config.get('mode', 'N/A')
            limit = config.get('limit', 'N/A')
            await io.print(f":: Rolling history is ON. Mode: {mode}, Limit: {limit}.")
        else:
            await io.print(":: Rolling history is OFF.")
        return True

    if len(argv) == 1:
        # Handle on/off
        action = argv[0].lower()
        if action == 'on':
            if not config.get('mode') or not config.get('limit'):
                await io.error("!! rolling: cannot enable without a mode and limit set first.")
                return False
            config['enabled'] = True
            await io.print(":: Rolling history enabled.")
        elif action == 'off':
            config['enabled'] = False
            await io.print(":: Rolling history disabled.")
        else:
            await io.error(f"!! rolling: unknown command '{action}'. Use 'on', 'off', or set a limit.")
            return False
        return True

    if len(argv) == 2:
        # Set mode and limit
        mode_arg = argv[0]
        limit_arg = argv[1]

        valid_modes = {
            '--tokens': 'tokens',
            '--bytes': 'bytes',
            '--lines': 'lines',
            '--prompts': 'prompts',
        }

        if mode_arg not in valid_modes:
            await io.error(f"!! rolling: invalid mode '{mode_arg}'. Valid modes are {', '.join(valid_modes.keys())}.")
            return False

        mode_key = valid_modes[mode_arg]

        try:
            limit_val = int(limit_arg)
            if limit_val <= 0:
                raise ValueError("Limit must be positive.")
        except ValueError:
            await io.error(f"!! rolling: limit must be a positive integer, not '{limit_arg}'.")
            return False

        config['mode'] = mode_key
        config['limit'] = limit_val
        config['enabled'] = True

        await io.print(f":: Rolling history enabled. Cutoff at {limit_val} {mode_key}.")
        # After setting a new limit, apply it immediately to prune if necessary.
        io._apply_rolling_cutoff()
        return True

    # Incorrect number of arguments
    await io.error("!! rolling: incorrect number of arguments. Use 'rolling --help'.")
    return False