#!/usr/bin/env python
# bin/whereami.py

DOCSTRING = """Display the configured hostname of the local IOSK system.

Usage: whereami
       whereami --help

Displays the unique hostname of the local IOSK system on the network,
as configured in /etc/hostname or derived at startup.
"""

async def iocall(io, argv):
    """Handle the 'whereami' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    if argv:
        await io.error("!! whereami: command takes no arguments. Use 'whereami --help'.")
        return False

    # The kernel reads /etc/hostname at startup and stores the result.
    # Accessing the kernel's state is the canonical way to get the hostname.
    hostname = io.os.hostname
    await io.print(hostname)

    return True
