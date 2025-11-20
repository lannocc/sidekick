async def iocall(io, argv):
    """Manage the IOSK system-wide tracing facility.

    Usage: trace
           trace on|off
           trace <name> on|off
           trace --help

    trace:
      Displays a list of all available trace points and their current state (ON/OFF).

    trace on|off:
      Enables or disables all available trace points.

    trace <name> on|off:
      Enables or disables a single, specific trace point by its name.

    --help:
      Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__.strip())
        return True

    trace_states = io.os.trace_states

    # Case 1: Display status (no arguments)
    if not argv:
        if not trace_states:
            await io.print(":: No trace points available.")
            return True
        
        trace_points = sorted(trace_states.keys())
        
        for name in trace_points:
            state = "ON" if trace_states.get(name, False) else "OFF"
            await io.print(f"{name}: {state}")
        return True

    # Case 2: Global on/off (one argument)
    if len(argv) == 1:
        state_str = argv[0].lower()
        if state_str == 'on':
            for key in trace_states:
                trace_states[key] = True
            await io.print(":: All traces set to ON")
            return True
        elif state_str == 'off':
            for key in trace_states:
                trace_states[key] = False
            await io.print(":: All traces set to OFF")
            return True
        else:
            await io.error(f"!! trace: invalid argument '{argv[0]}'. Use 'on', 'off', or see 'trace --help'.")
            return False

    # Case 3: Specific trace point on/off (two arguments)
    if len(argv) == 2:
        name = argv[0]
        state_str = argv[1].lower()

        # Validate trace name
        if name not in trace_states:
            await io.error(f"!! trace: unknown trace point '{name}'")
            return False

        # Validate state
        if state_str == 'on':
            trace_states[name] = True
            await io.print(f":: Trace '{name}' set to ON")
            return True
        elif state_str == 'off':
            trace_states[name] = False
            await io.print(f":: Trace '{name}' set to OFF")
            return True
        else:
            await io.error(f"!! trace: invalid state '{argv[1]}'. Use 'on' or 'off'.")
            return False

    # Case 4: Too many arguments
    await io.error("!! trace: too many arguments. Use 'trace --help' for usage.")
    return False
