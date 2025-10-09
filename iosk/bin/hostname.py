import os

DOCSTRING = """Display or set the system's hostname.

Usage: hostname
       hostname <new-hostname>
       hostname --help

hostname:
  Prints the current hostname as configured in /etc/hostname.

hostname <new-hostname>:
  Sets the system's hostname to the new value, updating both the
  /etc/hostname file and the current runtime configuration.
"""

async def iocall(io, argv):
    """Handle the 'hostname' command execution."""

    if '--help' in argv:
        await io.print(DOCSTRING.strip())
        return True

    # Case 1: Display hostname (no arguments)
    if not argv:
        hostname_path = '/etc/hostname'
        content = await io.os.get(io, hostname_path)
        if content is not None:
            await io.print(content.strip())
            return True
        else:
            # io.os.get already printed an error, so we fail.
            # As a fallback, we could print io.os.hostname, but sticking
            # to the file is more aligned with the standard command.
            return False

    # Case 2: Set hostname (one argument)
    if len(argv) == 1:
        new_hostname = argv[0].strip()
        
        # Basic validation for the new hostname.
        if not new_hostname or '/' in new_hostname or '\\' in new_hostname or any(c.isspace() for c in new_hostname):
            await io.error(f"!! hostname: '{new_hostname}' is not a valid hostname.")
            return False

        hostname_path_virtual = '/etc/hostname'
        hostname_path_host = io.os.box(hostname_path_virtual, io_context=io)

        try:
            # Write the new hostname to the configuration file.
            # The 'w' mode will create the file if it doesn't exist.
            with open(hostname_path_host, 'w', encoding='utf-8') as f:
                f.write(new_hostname)
            
            # Update the live hostname in the kernel for immediate effect.
            io.os.hostname = new_hostname
            
            await io.print(f":: hostname has been set to '{new_hostname}'")
            return True
        except Exception as e:
            await io.error(f"!! hostname: failed to write to {hostname_path_virtual}: {e}")
            return False

    # Case 3: Too many arguments
    await io.error("!! hostname: too many arguments. Use 'hostname --help' for usage.")
    return False
