async def iocall(io, argv):
    """Terminate a running process.

    Usage: kill <pid>
           kill --help

    <pid>: The Process ID (PID) of the process to terminate. Use the 'ps'
           command to find the PIDs of running processes.
    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if len(argv) != 1:
        await io.error("!! kill: requires exactly one argument: <pid>")
        return False

    pid_str = argv[0]

    # Validate that the PID is a number
    try:
        pid_to_kill = int(pid_str)
    except ValueError:
        await io.error(f"!! kill: invalid PID '{pid_str}'. PID must be a number.")
        return False

    # Access the process table from the kernel
    process_table = io.os.proc.process_table

    # Check if the process exists
    if pid_to_kill not in process_table:
        await io.error(f"!! kill: no such process with PID: {pid_to_kill}")
        return False

    # Retrieve the process and cancel its underlying asyncio.Task
    process = process_table[pid_to_kill]
    process.task.cancel()

    # The executor's finally block will handle cleanup and printing the final
    # "cancelled" message. This command's job is just to send the signal.
    await io.print(f":: Process {pid_to_kill} ({process.command_str}) has been signalled to terminate.")

    return True
