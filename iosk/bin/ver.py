# iosk/bin/ver.py

from sk.__version__ import __version__

async def iocall(io, argv):
    """Display the current version of SideKick.

    Usage: ver
           ver --help

    --help: Displays this help message.
    """
    if '--help' in argv:
        await io.print(iocall.__doc__)
        return True

    if argv:
        await io.error('!! ver: does not accept arguments. Try `ver --help`.')
        return False

    await io.print(__version__)
    return True

