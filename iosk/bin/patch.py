import subprocess
import asyncio

async def iocall(io, args):
    """Apply a patch to a file.

    Usage: patch [-p <number>] <patchfile>
           patch --help

    -p <number>: Specifies the number of leading directory components to strip. Defaults to 1.
    <patchfile>: The path to the patch file.
    --help: Displays this help message.
    """

    if '--help' in args:
        await io.print(iocall.__doc__)
        return

    args = args.split(' ')
    if not args:
        await io.error('!! patch: patchfile required')
        return

    # Handle redirection-like argument (patch -p1 <patchfile)
    if len(args) >= 2 and args[-2] == '<':
        patchfile = args[-1]
        patch_args = args[:-2]  # patch -p1
    else:
        patchfile = args[-1] #patch myfile.patch
        patch_args = args[:-1] #patch

    try:
        patch_file_path = io.os.box(patchfile)

        with open(patch_file_path, 'r') as patch_file:
            patch_process = await asyncio.create_subprocess_exec(
                'patch',
                *patch_args,
                stdin=patch_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

        stdout, stderr = await patch_process.communicate()

        if stdout:
            await io.print(stdout.decode())
        if stderr:
            await io.error(stderr.decode())

        if patch_process.returncode != 0:
            await io.error(f'!! patch: apply failed with code {patch_process.returncode}')
            return False

        await io.print(':: patch applied')
        return True

    except FileNotFoundError:
        await io.error(f'!! patch: patch file not found: {patchfile}')
        return False
    except Exception as e:
        await io.error(f'!! patch: error applying patch: {e}')
        return False

