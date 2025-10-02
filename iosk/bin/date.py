from datetime import datetime

async def iocall(io, argv):
    """Display the current date and time, with optional formatting.

    Usage: date
           date <format>
           date --help

    <format>: A format string to control the output. The format string
              should start with a '+'. For example: "+%Y%m%d_%H%M%S".
              Uses Python's datetime strftime format codes.
              If no format is provided, a default format is used.
    --help: Displays this help message.
    """

    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    # Default format
    format_string = '%A, %b %d, %Y at %I:%M:%S %p'

    if argv:
        if len(argv) == 1:
            arg = argv[0]
            if arg.startswith('+'):
                format_string = arg[1:] # Remove the leading '+'
            else:
                await io.error(f"!! date: invalid argument '{arg}'. Use 'date --help' for usage, or specify a format starting with '+'.")
                return False
        else:
            await io.error("!! date: too many arguments. Use 'date --help' for usage.")
            return False

    try:
        await io.print(datetime.now().strftime(format_string))
        return True
    except ValueError as e:
        await io.error(f"!! date: invalid format string: {e}")
        return False
    except Exception as e:
        await io.error(f"!! date: an unexpected error occurred: {e}")
        return False

